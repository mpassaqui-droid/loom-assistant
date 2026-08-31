"""FastAPI wrapper around LoomAgent.

Bring-your-own-key: each request supplies its own provider + API key
(Anthropic, OpenAI, or Google). The key is used only to make that request's
model calls and is never stored, logged, or written to disk — see
SECURITY.md. This is also what makes the demo free to host: Munay's account
is never billed for a visitor's usage.

A basic rate limit and input-length cap are the safety/ethics pass for this
project — the LOOM domain itself has a narrow attack surface, so this stays
deliberately light.
"""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from core.agent import LoomAgent

app = FastAPI(title="LOOM Assistant", description="RAG + agent that writes and validates LOOM code.")

_request_log: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_PER_MINUTE = 10
MAX_QUESTION_LEN = 500


class AskRequest(BaseModel):
    question: str = Field(..., max_length=MAX_QUESTION_LEN)
    provider: Literal["anthropic", "openai", "google"]
    api_key: str = Field(..., description="Your own API key for the chosen provider. Never stored or logged.")


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
    _check_rate_limit("global")  # no auth layer: one shared bucket, fine for a demo
    agent = LoomAgent(provider=req.provider, api_key=req.api_key)
    try:
        result = agent.ask(req.question)
    except Exception as exc:  # a bad/expired key from a provider surfaces here
        raise HTTPException(status_code=400, detail=f"model call failed: {exc}") from None
    return AskResponse(**result)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
