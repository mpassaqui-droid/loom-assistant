"""FastAPI wrapper around LoomAgent.

Single endpoint: POST /ask {"question": "..."} -> agent answer + validation
report. A basic rate limit and input-length cap are the safety/ethics pass
for this project (see SECURITY.md) — the LOOM domain itself has a narrow
attack surface, so this stays deliberately light.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from core.agent import LoomAgent

app = FastAPI(title="LOOM Assistant", description="RAG + agent that writes and validates LOOM code.")

_agent: LoomAgent | None = None
_request_log: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_PER_MINUTE = 10
MAX_QUESTION_LEN = 500


def get_agent() -> LoomAgent:
    global _agent
    if _agent is None:
        _agent = LoomAgent()
    return _agent


class AskRequest(BaseModel):
    question: str = Field(..., max_length=MAX_QUESTION_LEN)


class AskResponse(BaseModel):
    answer: str
    turns: int
    validated: bool
    last_validation: dict | None


def _check_rate_limit(client_id: str) -> None:
    now = time.monotonic()
    window = [t for t in _request_log[client_id] if now - t < 60]
    if len(window) >= RATE_LIMIT_PER_MINUTE:
        raise HTTPException(status_code=429, detail="rate limit exceeded, try again in a minute")
    window.append(now)
    _request_log[client_id] = window


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    _check_rate_limit("global")  # no auth layer yet: one shared bucket, fine for a demo
    result = get_agent().ask(req.question)
    return AskResponse(**result)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
