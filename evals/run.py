"""Run the full golden set through the real agent and report real numbers.

Never prints "it works" without running it. Requires ANTHROPIC_API_KEY set —
this calls the live agent (core.agent.LoomAgent), not a stand-in.
"""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

from core.agent import LoomAgent
from evals.checks import CHECKS

GOLDEN_SET = Path(__file__).parent / "golden_set.jsonl"


def load_golden_set() -> list[dict]:
    return [json.loads(line) for line in GOLDEN_SET.read_text().splitlines() if line.strip()]


def main() -> None:
    examples = load_golden_set()
    agent = LoomAgent()

    results = []
    latencies = []
    for ex in examples:
        start = time.monotonic()
        outcome = agent.ask(ex["prompt"])
        elapsed = time.monotonic() - start
        latencies.append(elapsed)

        report = outcome.get("last_validation") or {}
        check_fn = CHECKS[ex["check"]]
        passed = "error" not in report and check_fn(report, ex["params"])

        results.append({"id": ex["id"], "passed": passed, "turns": outcome["turns"], "latency_s": round(elapsed, 2)})
        print(f"{'PASS' if passed else 'FAIL'}  {ex['id']:20s}  {outcome['turns']} turns  {elapsed:.2f}s")

    n = len(results)
    n_pass = sum(1 for r in results if r["passed"])
    p50 = statistics.median(latencies)
    p95 = statistics.quantiles(latencies, n=20)[18] if n >= 5 else max(latencies)

    print()
    print(f"Semantic pass rate: {n_pass}/{n} ({100 * n_pass / n:.0f}%)")
    print(f"Latency: p50={p50:.2f}s  p95={p95:.2f}s")

    sys.exit(0 if n_pass == n else 1)


if __name__ == "__main__":
    main()
