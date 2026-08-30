# Stage 1: compile the validator binary. loom-core itself is vendored in via
# a build-context copy (see .dockerignore) — the loom repo is not touched,
# just read from at build time, same as at dev time.
FROM rust:1.82-slim AS validator-build
WORKDIR /build
COPY validator/ validator/
COPY loom-core-src/ loom-core-src/
RUN sed -i 's#path = "/Users/[^"]*"#path = "../loom-core-src"#' validator/Cargo.toml \
    && cd validator && cargo build --release

# Stage 2: the actual app image.
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ core/
COPY api/ api/
COPY evals/ evals/
COPY --from=validator-build /build/validator/target/release/loom-validate validator/target/release/loom-validate

# The retriever needs a live Ollama reachable at OLLAMA_HOST for embeddings.
# For the demo deployment this points at a small managed Ollama instance or a
# sidecar container (see docker-compose.yml for local use).
ENV OLLAMA_HOST=http://localhost:11434

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
