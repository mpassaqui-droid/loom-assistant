"""Agentic RAG loop for loom-assistant — provider-agnostic (see
core/providers.py): each caller (a demo visitor, via the API) brings their
own API key for whichever of Anthropic/OpenAI/Google they want to try. The
key is used only for the calls made during this one .ask() and is never
stored, logged, or written to disk (see SECURITY.md).

Same shape as Rimay's core/boucle.py: the model holds real tools and sees
each tool's result before deciding what to do next, rather than a
single-shot generate-and-hope. Two tools:

- chercher_docs: the hybrid retriever (core.rag).
- valider_loom: shells out to the real loom-core parser/scheduler (the
  `loom-validate` Rust binary) and returns exactly what it reports. The
  model never gets to claim success on its own say-so — every generated
  pattern is checked against the actual engine before the agent hands it
  back.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from core.providers import Conversation, call_model
from core.rag import HybridRetriever

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


def valider_loom(code: str) -> dict:
    if not VALIDATOR_BIN.exists():
        return {"error": f"validator binary not built: {VALIDATOR_BIN}"}
    result = subprocess.run(
        [str(VALIDATOR_BIN)], input=code, capture_output=True, text=True, timeout=5
    )
    if result.returncode != 0:
        return {"error": result.stderr.strip() or "validator exited non-zero"}
    return json.loads(result.stdout)


# The retriever loads 104 chunks and computes a BM25 index over them — cheap,
# but no reason to redo it per request. Shared across all providers/keys,
# since it never touches a user's API key.
_shared_retriever: HybridRetriever | None = None


def _get_retriever() -> HybridRetriever:
    global _shared_retriever
    if _shared_retriever is None:
        _shared_retriever = HybridRetriever()
    return _shared_retriever


class LoomAgent:
    def __init__(self, provider: str, api_key: str) -> None:
        self.provider = provider
        self.api_key = api_key
        self.retriever = _get_retriever()

    def _run_tool(self, name: str, tool_input: dict) -> str:
        if name == "chercher_docs":
            chunks = self.retriever.retrieve(tool_input["query"], k=4)
            return "\n\n".join(f"[{c.source}]\n{c.text}" for c in chunks)
        if name == "valider_loom":
            return json.dumps(valider_loom(tool_input["code"]))
        return f"unknown tool: {name}"

    def ask(self, question: str) -> dict:
        """Returns {"answer": str, "turns": int, "validated": bool, "last_validation": dict|None}."""
        conversation = Conversation(self.provider)
        conversation.add_user(question)
        last_validation = None

        for turn in range(MAX_TURNS):
            model_turn, raw = call_model(self.provider, self.api_key, SYSTEM_PROMPT, conversation)

            if model_turn.is_final:
                return {
                    "answer": model_turn.text,
                    "turns": turn + 1,
                    "validated": last_validation is not None,
                    "last_validation": last_validation,
                }

            conversation.add_assistant_turn(raw)
            results = []
            for call in model_turn.tool_calls:
                output = self._run_tool(call.name, call.input)
                if call.name == "valider_loom":
                    try:
                        parsed = json.loads(output)
                        last_validation = parsed if "error" not in parsed else {"error": output}
                    except json.JSONDecodeError:
                        last_validation = {"error": output}
                results.append((call, output))
            conversation.add_tool_results(results)

        return {
            "answer": "Ran out of turns without a final answer.",
            "turns": MAX_TURNS,
            "validated": last_validation is not None,
            "last_validation": last_validation,
        }
