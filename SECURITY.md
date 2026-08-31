# Security & data

- `loom-core`'s source is private by Munay's own choice, not for security
  reasons — see `tasks/lessons.md`. Only a compiled binary
  (`validator/prebuilt/loom-validate-linux-x86_64`) is committed here, never
  the source. This repo is fully buildable and deployable by anyone without
  access to that private repo.

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
- Secrets: for local dev, `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`GOOGLE_API_KEY` and Langfuse keys
  are read from environment variables only, never committed. `.gitignore` excludes `.env*`.
- **Bring-your-own-key on the deployed demo**: each `/ask` request carries its own `provider` +
  `api_key` (see `core/providers.py`). That key is used only for the model calls made during that
  one request, held only in memory for the lifetime of the request, and is never written to disk,
  logged, or sent to Langfuse (Langfuse traces record the question/answer/latency, not the key).
  This is also what keeps the demo free to host — Munay's own account is never billed for a
  visitor's usage.
