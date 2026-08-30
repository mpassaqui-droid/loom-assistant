"""Agentic RAG loop for loom-assistant.

Same shape as Rimay's core/boucle.py: Claude holds real tools and sees each
tool's result before deciding what to do next, rather than a single-shot
generate-and-hope. Two tools:

- chercher_docs: the hybrid retriever (core.rag).
- valider_loom: shells out to the real loom-core parser/scheduler (the
  `loom-validate` Rust binary) and returns exactly what it reports. The model
  never gets to claim success on its own say-so — every generated pattern is
  checked against the actual engine before the agent hands it back.

Needs a real ANTHROPIC_API_KEY at runtime (this is the deployed product
calling the API on its own account, not Claude Code — different context from
the "don't set ANTHROPIC_API_KEY, bill the subscription" rule in ~/Dev/loom's
own CLAUDE.md, which is about using Claude Code as a dev tool).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import anthropic

from core.rag import HybridRetriever

MODEL = "claude-sonnet-4-5-20250929"
VALIDATOR_BIN = Path(__file__).parent.parent / "validator" / "target" / "release" / "loom-validate"
MAX_TURNS = 6

SYSTEM_PROMPT = """You are LOOM Assistant, an expert in LOOM, a minimal live-coding music \
language (one voice per line, `x`/`.` for drums, note names for melody, verbs like `rev`/\
`fast N`/`every N <verb>`).

You have two tools:
- chercher_docs: search LOOM's own documentation and example patterns for relevant syntax.
- valider_loom: run a piece of LOOM code through the REAL parser/scheduler and see exactly \
what it would play (voices, scheduled events, their timing). This is the only source of truth \
about whether generated code actually does what was asked — the parser is permissive and never \
raises an error, so you must check event_count and the actual event phases/voices yourself, \
not assume success.

Always use chercher_docs before writing LOOM code you're not certain about. Always use \
valider_loom on code you generate before presenting it as a final answer. If the validation \
shows the wrong number of voices, wrong events, or an empty result, revise the code and \
validate again — never present unvalidated code as a working answer."""

TOOLS = [
    {
        "name": "chercher_docs",
        "description": "Search LOOM's documentation and example patterns for syntax relevant to a question.",
        "input_schema": {
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
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "LOOM source to validate"}},
            "required": ["code"],
        },
    },
]


def valider_loom(code: str) -> dict:
    if not VALIDATOR_BIN.exists():
        return {"error": f"validator binary not built: {VALIDATOR_BIN}"}
    result = subprocess.run(
        [str(VALIDATOR_BIN)], input=code, capture_output=True, text=True, timeout=5
    )
    if result.returncode != 0:
        return {"error": result.stderr.strip() or "validator exited non-zero"}
    return json.loads(result.stdout)


class LoomAgent:
    def __init__(self) -> None:
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.retriever = HybridRetriever()

    def _run_tool(self, name: str, tool_input: dict) -> str:
        if name == "chercher_docs":
            chunks = self.retriever.retrieve(tool_input["query"], k=4)
            return "\n\n".join(f"[{c.source}]\n{c.text}" for c in chunks)
        if name == "valider_loom":
            return json.dumps(valider_loom(tool_input["code"]))
        return f"unknown tool: {name}"

    def ask(self, question: str) -> dict:
        """Returns {"answer": str, "turns": int, "validated": bool, "last_validation": dict|None}."""
        messages = [{"role": "user", "content": question}]
        last_validation = None
        for turn in range(MAX_TURNS):
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )
            if response.stop_reason != "tool_use":
                text = "".join(b.text for b in response.content if b.type == "text")
                return {
                    "answer": text,
                    "turns": turn + 1,
                    "validated": last_validation is not None,
                    "last_validation": last_validation,
                }

            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                output = self._run_tool(block.name, block.input)
                if block.name == "valider_loom":
                    last_validation = json.loads(output) if not output.startswith("{\"error\"") else {"error": output}
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": output}
                )
            messages.append({"role": "user", "content": tool_results})

        return {
            "answer": "Ran out of turns without a final answer.",
            "turns": MAX_TURNS,
            "validated": last_validation is not None,
            "last_validation": last_validation,
        }
