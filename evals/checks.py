"""Semantic checks against the real loom-validate oracle.

Each function takes the JSON report from `loom-validate` (voices/events
actually scheduled, from the real engine — never the LLM's own claim) plus the
golden-set example's params, and returns True/False. These are the ground
truth for the eval; see core/agent.py for why "did it parse" alone is not a
meaningful signal (loom-core's parser never errors, even on garbage).
"""

from __future__ import annotations


def kick_on_phases(report: dict, params: dict) -> bool:
    wanted = set(round(p, 3) for p in params["phases"])
    got = {round(e["phase"], 3) for e in report.get("events", []) if e["voice"] == params["voice"]}
    return wanted.issubset(got)


def event_count_for_voice(report: dict, params: dict) -> bool:
    count = sum(1 for e in report.get("events", []) if e["voice"] == params["voice"])
    if "min_count" in params and count < params["min_count"]:
        return False
    if "max_count" in params and count > params["max_count"]:
        return False
    return True


def voice_count(report: dict, params: dict) -> bool:
    return report.get("voice_count", 0) >= params["min_voices"]


def bpm_equals(report: dict, params: dict) -> bool:
    bpm = report.get("bpm")
    return bpm is not None and abs(bpm - params["bpm"]) < 0.5


def has_pitched_voice(report: dict, params: dict) -> bool:
    return any(not v["is_drum"] for v in report.get("voices", []))


def exact_phases(report: dict, params: dict) -> bool:
    """Stricter than kick_on_phases: the voice must hit EXACTLY these phases,
    no more, no fewer — for prompts that ask for one precise hit pattern."""
    wanted = set(round(p, 3) for p in params["phases"])
    got = {round(e["phase"], 3) for e in report.get("events", []) if e["voice"] == params["voice"]}
    return wanted == got


def voice_has_verb(report: dict, params: dict) -> bool:
    """Did the requested transformation verb (rev, fast, swing, arp...)
    actually get applied to the named voice? Checked against the real parsed
    Voice.verbs list, not the LLM's claim that it applied one."""
    substring = params["verb_substring"]
    for v in report.get("voices", []):
        if v["name"] == params["voice"] and any(substring in verb for verb in v.get("verbs", [])):
            return True
    return False


CHECKS = {
    "kick_on_phases": kick_on_phases,
    "event_count_for_voice": event_count_for_voice,
    "voice_count": voice_count,
    "bpm_equals": bpm_equals,
    "has_pitched_voice": has_pitched_voice,
    "exact_phases": exact_phases,
    "voice_has_verb": voice_has_verb,
}
