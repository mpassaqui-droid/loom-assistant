# LOOM Assistant

An agent that writes LOOM code (a minimal live-coding music language, see the
companion [loom](https://github.com/mpassaqui-droid/loom-showcase) project)
and checks its own work against the real engine before answering.

## What it does

Ask a question in plain English ("a kick and snare pattern at 140 BPM"), and
the agent:

1. Retrieves relevant syntax from LOOM's own docs and 62 example patterns
   (hybrid retrieval: dense embeddings + BM25, merged by reciprocal rank
   fusion).
2. Generates LOOM code.
3. Runs it through the real `loom-core` parser and scheduler — not a
   simulation, the actual engine LOOM itself uses — and checks the scheduled
   events against what was asked.
4. If the result doesn't match, retries with the real error/mismatch as
   context, instead of presenting unverified code.

The parser is permissive by design (it never raises an error, even on
garbage input), so "did it parse" is not a real signal on its own. The eval
harness (`evals/`) checks the actual scheduled events — voice count, timing,
tempo — against each golden-set example's stated intent.

## Stack

Python 3.11, Anthropic API (tool use), local embeddings via Ollama
(`nomic-embed-text`), Chroma for vector storage, BM25 (`rank_bm25`) for the
sparse side of retrieval, Langfuse for tracing/latency/cost, FastAPI, Docker.

## Status

Active development. The RAG pipeline and the validation oracle are tested
and passing (`pytest tests/` — 13/13 on the check-function suite, run
against the real `loom-validate` binary, not a mock). The end-to-end agent
loop needs a live `ANTHROPIC_API_KEY` to run; `evals/run.py` reports honest
pass-rate and latency numbers once one is set, they are not filled in here
until a real run has produced them.

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd validator && cargo build --release && cd ..
python3 -m core.rag              # build the retrieval index (needs Ollama running)
export ANTHROPIC_API_KEY=sk-...
python3 -m evals.run             # run the golden set, print real numbers
uvicorn api.main:app --reload    # or serve it
```

## Deployment note

The retriever calls a local Ollama for embeddings. Running Ollama on a small
hosted instance (Render/Railway free tier) is not guaranteed to work well —
if the deployed demo needs to swap to a hosted embeddings API instead of
local Ollama, that's a one-line change in `core/rag.py::_embed`, not a
redesign.
