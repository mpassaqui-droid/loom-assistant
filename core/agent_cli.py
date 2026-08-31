"""Alternate agent runtime: same interface as core.agent.LoomAgent, but backed
by `claude -p` (Claude Code CLI, non-interactive) instead of the Anthropic
SDK — uses the machine's authenticated Claude Code session (subscription),
no ANTHROPIC_API_KEY needed. Restricted to the Bash tool only, which it uses
to call scripts/search_docs.py and the loom-validate binary — the same two
tools as core.agent, just invoked as shell commands instead of the
tool_use API protocol.

Good for: local development and testing without an API key.
NOT appropriate for: the deployed public demo (Phase 6). A personal
subscription authenticates one person's interactive use of Claude Code; it
is not meant to back a public-facing API taking arbitrary traffic, and a
deployed server can't practically carry a personal login session. The live
demo still needs a real ANTHROPIC_API_KEY (core.agent.LoomAgent) — this
module only unblocks testing the RAG+validation design for free, right now.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

PROMPT_TEMPLATE = """Tu es un assistant LOOM. Utilise UNIQUEMENT ces deux commandes bash :
1. python3 scripts/search_docs.py "<requete>" — cherche dans la doc/exemples LOOM
2. echo '<code loom>' | validator/target/release/loom-validate — valide un pattern contre le VRAI moteur (parse + planification réelle)

loom-validate ne renvoie JAMAIS d'erreur, meme sur du charabia (0 voix, 0 event = echec silencieux).
Ne presente jamais un code comme correct sans l'avoir valide et sans avoir verifie que le JSON
de sortie correspond vraiment a la demande (bon nombre de voix, bons events, bonnes phases).

Question : {question}

Cherche la doc si besoin, ecris le code, valide-le, corrige si le JSON ne correspond pas a la
demande. Termine TOUJOURS ta reponse par le JSON exact de la DERNIERE validation reussie, dans
un bloc ```json, rien d'autre dedans."""


def _extract_last_json_block(text: str) -> dict | None:
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not blocks:
        return None
    try:
        return json.loads(blocks[-1])
    except json.JSONDecodeError:
        return None


class LoomAgentCLI:
    def __init__(self, model: str | None = None) -> None:
        # Alias (e.g. "sonnet", "opus", "fable") or a full model name
        # ("claude-sonnet-4-5-20250929"). None = Claude Code's own default.
        self.model = model

    def ask(self, question: str) -> dict:
        prompt = PROMPT_TEMPLATE.format(question=question)
        cmd = ["claude", "-p", "--allowedTools", "Bash"]
        if self.model:
            cmd += ["--model", self.model]
        start = time.monotonic()
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=120,
        )
        elapsed = time.monotonic() - start
        answer = result.stdout.strip()
        validation = _extract_last_json_block(answer)
        return {
            "answer": answer,
            "turns": None,  # not tracked in this runtime
            "validated": validation is not None,
            "last_validation": validation,
            "elapsed_s": elapsed,
        }
