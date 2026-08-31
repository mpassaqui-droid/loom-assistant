"""Run the full golden set through a real agent and report real numbers.

Never prints "it works" without running it.

Two runtimes:
- --runtime api (default when ANTHROPIC_API_KEY is set): core.agent.LoomAgent,
  the real deployed path.
- --runtime cli: core.agent_cli.LoomAgentCLI, via `claude -p` on the local
  Claude Code subscription — no API key needed, for local dev only (see
  core/agent_cli.py for why this isn't used for the deployed demo).
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

from evals.checks import CHECKS

GOLDEN_SET = Path(__file__).parent / "golden_set.jsonl"


def load_golden_set() -> list[dict]:
    return [json.loads(line) for line in GOLDEN_SET.read_text().splitlines() if line.strip()]


PROVIDER_ENV_VAR = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", choices=["api", "cli"], default="cli")
    parser.add_argument("--provider", choices=list(PROVIDER_ENV_VAR), default="anthropic")
    parser.add_argument("--model", default=None, help="cli runtime only: e.g. sonnet, opus, fable")
    args = parser.parse_args()

    if args.runtime == "cli":
        from core.agent_cli import LoomAgentCLI
        agent = LoomAgentCLI(model=args.model)
    else:
        from core.agent import LoomAgent
        env_var = PROVIDER_ENV_VAR[args.provider]
        api_key = os.environ.get(env_var)
        if not api_key:
            sys.exit(f"--runtime api --provider {args.provider} needs {env_var} set")
        agent = LoomAgent(provider=args.provider, api_key=api_key)

    examples = load_golden_set()

    results = []
    latencies = []
    total_cost = 0.0
    for ex in examples:
        start = time.monotonic()
        outcome = agent.ask(ex["prompt"])
        elapsed = time.monotonic() - start
        latencies.append(elapsed)
        total_cost += outcome.get("cost_usd") or 0.0

        report = outcome.get("last_validation") or {}
        check_fn = CHECKS[ex["check"]]
        passed = "error" not in report and check_fn(report, ex["params"])

        turns_label = f"{outcome['turns']} turns" if outcome.get("turns") is not None else "n/a turns"
        cost_label = f"${outcome['cost_usd']:.5f}" if outcome.get("cost_usd") is not None else "n/a cost"
        results.append({"id": ex["id"], "passed": passed, "turns": outcome.get("turns"), "latency_s": round(elapsed, 2)})
        print(f"{'PASS' if passed else 'FAIL'}  {ex['id']:20s}  {turns_label}  {elapsed:.2f}s  {cost_label}")

    n = len(results)
    n_pass = sum(1 for r in results if r["passed"])
    p50 = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18] if n >= 5 else max(latencies)

    print()
    print(f"Semantic pass rate: {n_pass}/{n} ({100 * n_pass / n:.0f}%)")
    print(f"Latency: p50={p50:.2f}s  p95={p95:.2f}s")
    print(f"Total cost: ${total_cost:.5f} (n/a if --runtime cli — claude -p doesn't expose token usage)")

    sys.exit(0 if n_pass == n else 1)


if __name__ == "__main__":
    main()
