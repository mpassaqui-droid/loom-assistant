"""Unit tests for the eval checks, run against the REAL loom-validate binary
on hand-written LOOM snippets. This proves the grading logic itself is
correct, independent of whether an LLM ever produces good code — the same
separation of concerns as Rimay's "verify the tester before accusing the
agent" lesson.
"""

import json
import subprocess
from pathlib import Path

import pytest

from evals.checks import CHECKS

VALIDATOR_BIN = Path(__file__).parent.parent / "validator" / "target" / "release" / "loom-validate"


def validate(code: str) -> dict:
    result = subprocess.run([str(VALIDATOR_BIN)], input=code, capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize(
    "code,check_name,params,expected",
    [
        ("kick: x . x .", "kick_on_phases", {"voice": "kick", "phases": [0.0, 0.5]}, True),
        ("kick: x . . .", "kick_on_phases", {"voice": "kick", "phases": [0.0, 0.5]}, False),
        ("kick: x x x x", "event_count_for_voice", {"voice": "kick", "min_count": 4}, True),
        ("kick: x . . .", "event_count_for_voice", {"voice": "kick", "min_count": 4}, False),
        ("kick: . . . .", "event_count_for_voice", {"voice": "kick", "max_count": 0}, True),
        ("kick: x . . .", "event_count_for_voice", {"voice": "kick", "max_count": 0}, False),
        ("kick: x . x .\nsnare: . x . x", "voice_count", {"min_voices": 2}, True),
        ("kick: x . x .", "voice_count", {"min_voices": 2}, False),
        ("bpm: 140\nkick: x . x .", "bpm_equals", {"bpm": 140}, True),
        ("bpm: 100\nkick: x . x .", "bpm_equals", {"bpm": 140}, False),
        ("lead: c4 e4 g4 c5", "has_pitched_voice", {}, True),
        ("kick: x . x .", "has_pitched_voice", {}, False),
        ("this is garbage not loom at all", "voice_count", {"min_voices": 1}, False),
    ],
)
def test_check_against_real_oracle(code, check_name, params, expected):
    report = validate(code)
    assert CHECKS[check_name](report, params) is expected
