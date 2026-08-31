#!/usr/bin/env python3
"""Personal, local-only entry point: ask LOOM Assistant a question via your
own Claude Code subscription (`claude -p`), free, with a choice of model.
Never exposed on the public API — see core/agent_cli.py.

Usage:
    python3 scripts/ask_local.py "a kick and snare pattern at 140 BPM"
    python3 scripts/ask_local.py --model opus "a euclidean kick, 3 hits over 8 steps"
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agent_cli import LoomAgentCLI

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--model", default=None, help="e.g. sonnet, opus, fable, or a full model name")
    args = parser.parse_args()

    agent = LoomAgentCLI(model=args.model)
    result = agent.ask(args.question)

    print(result["answer"])
    print()
    print(f"[model={args.model or 'default'}  elapsed={result['elapsed_s']:.1f}s  validated={result['validated']}]")
    if result["last_validation"]:
        print(json.dumps(result["last_validation"], indent=2))
