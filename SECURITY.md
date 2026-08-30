# Security & data

- Data used: only LOOM's own public docs and example patterns (`~/Dev/loom`,
  ingested read-only). No user data is stored — questions are not logged
  anywhere except in Langfuse traces (latency/cost/debugging), which hold no
  PII since nothing personal is ever part of a question about LOOM syntax.
- Prompt injection: the retrieved context (docs/examples) is treated as data,
  not instructions, in the system prompt. The domain's narrow scope (a small
  music language) limits what an injected instruction could realistically
  achieve even if it slipped through.
- Rate limiting: 10 requests/minute, shared bucket (no auth layer for this
  demo — add per-key limits before any real multi-user deployment).
- Secrets: `ANTHROPIC_API_KEY` and Langfuse keys are read from environment
  variables only, never committed. `.gitignore` excludes `.env*`.
