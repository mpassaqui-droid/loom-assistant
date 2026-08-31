"""Provider-agnostic model calling: bring-your-own-key, any of the three top
providers (Anthropic, OpenAI, Google). This is what makes the deployed demo
free for Munay to host — each visitor supplies their own API key for the
model they want to try, per request, never stored or logged (see
SECURITY.md). This is also a real example of "model routing" (one of the
original 10 skill terms) rather than just a checkbox: the same agent loop
runs identically against three different backends.

VERIFIED: only the Anthropic adapter has been exercised end-to-end (via
`claude -p` locally, see core/agent_cli.py and tasks/todo.md — 8/8 on the
golden set). The OpenAI and Google adapters are written to each provider's
documented tool-calling shape but have NOT been run against a live key in
this environment (no OpenAI/Google key available to test with). The first
real test of those two paths will be a visitor's own key on the deployed demo
— flagged here rather than claimed as working.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

# Canonical tool spec, provider-agnostic. Each entry is converted to the
# shape each SDK expects at call time.
TOOL_SPECS = [
    {
        "name": "chercher_docs",
        "description": "Search LOOM's documentation and example patterns for syntax relevant to a question.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What to search for"}},
            "required": ["query"],
        },
    },
    {
        "name": "valider_loom",
        "description": (
            "Run LOOM source through the real parser and scheduler. Returns the actual voices "
            "parsed and events scheduled for bar 0 — the ground truth for whether the code works."
        ),
        "parameters": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "LOOM source to validate"}},
            "required": ["code"],
        },
    },
]


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict


@dataclass
class ModelTurn:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def is_final(self) -> bool:
        return not self.tool_calls


class Conversation:
    """Provider-specific message history, built up turn by turn. Each
    provider adapter knows how to append a user question, its own assistant
    turn, and tool results in its own required shape."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        self._messages: list = []

    def add_user(self, text: str) -> None:
        if self.provider == "anthropic":
            self._messages.append({"role": "user", "content": text})
        elif self.provider == "openai":
            self._messages.append({"role": "user", "content": text})
        elif self.provider == "google":
            self._messages.append({"role": "user", "parts": [{"text": text}]})

    def add_assistant_turn(self, raw_response) -> None:
        """Append the raw provider response as the assistant turn, in
        whatever shape that provider needs to see it echoed back."""
        if self.provider == "anthropic":
            self._messages.append({"role": "assistant", "content": raw_response.content})
        elif self.provider == "openai":
            self._messages.append(raw_response.choices[0].message.model_dump())
        elif self.provider == "google":
            self._messages.append(
                {"role": "model", "parts": [p.to_json_dict() for p in raw_response.candidates[0].content.parts]}
            )

    def add_tool_results(self, results: list[tuple[ToolCall, str]]) -> None:
        if self.provider == "anthropic":
            self._messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": tc.id, "content": out}
                        for tc, out in results
                    ],
                }
            )
        elif self.provider == "openai":
            for tc, out in results:
                self._messages.append({"role": "tool", "tool_call_id": tc.id, "content": out})
        elif self.provider == "google":
            self._messages.append(
                {
                    "role": "user",
                    "parts": [
                        {"function_response": {"name": tc.name, "response": {"result": out}}}
                        for tc, out in results
                    ],
                }
            )


def call_model(provider: str, api_key: str, system: str, conversation: Conversation) -> tuple[ModelTurn, object]:
    """Returns (normalized ModelTurn, raw provider response) — the raw
    response is what Conversation.add_assistant_turn needs to echo back."""
    if provider == "anthropic":
        return _call_anthropic(api_key, system, conversation)
    if provider == "openai":
        return _call_openai(api_key, system, conversation)
    if provider == "google":
        return _call_google(api_key, system, conversation)
    raise ValueError(f"unsupported provider: {provider!r} (expected anthropic, openai, or google)")


def _call_anthropic(api_key: str, system: str, conversation: Conversation):
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    tools = [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in TOOL_SPECS]
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        system=system,
        tools=tools,
        messages=conversation._messages,
    )
    text = "".join(b.text for b in response.content if b.type == "text")
    calls = [ToolCall(id=b.id, name=b.name, input=b.input) for b in response.content if b.type == "tool_use"]
    return ModelTurn(text=text, tool_calls=calls), response


def _call_openai(api_key: str, system: str, conversation: Conversation):
    import openai

    client = openai.OpenAI(api_key=api_key)
    tools = [
        {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
        for t in TOOL_SPECS
    ]
    messages = [{"role": "system", "content": system}, *conversation._messages]
    response = client.chat.completions.create(model="gpt-4.1", messages=messages, tools=tools)
    message = response.choices[0].message
    calls = [
        ToolCall(id=tc.id, name=tc.function.name, input=json.loads(tc.function.arguments))
        for tc in (message.tool_calls or [])
    ]
    return ModelTurn(text=message.content or "", tool_calls=calls), response


def _call_google(api_key: str, system: str, conversation: Conversation):
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    tool = types.Tool(function_declarations=[
        types.FunctionDeclaration(name=t["name"], description=t["description"], parameters=t["parameters"])
        for t in TOOL_SPECS
    ])
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=conversation._messages,
        config=types.GenerateContentConfig(system_instruction=system, tools=[tool]),
    )
    parts = response.candidates[0].content.parts
    text = "".join(p.text for p in parts if getattr(p, "text", None))
    calls = [
        ToolCall(id=p.function_call.name, name=p.function_call.name, input=dict(p.function_call.args))
        for p in parts
        if getattr(p, "function_call", None)
    ]
    return ModelTurn(text=text, tool_calls=calls), response
