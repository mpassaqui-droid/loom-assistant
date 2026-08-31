# Stage 1: compile the validator binary. loom-core's source is fetched
# straight from its own public repo at build time (a local script vendors it
# for local dev — see scripts/vendor_loom_core.sh — but a Render build has no
# access to Munay's filesystem, and loom-core-src/ is gitignored on purpose:
# it's a build artifact, not something to duplicate into this repo's git
# history). The loom repo itself is never modified, only cloned read-only.
FROM rust:1.82-slim AS validator-build
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
RUN git clone --depth 1 https://github.com/mpassaqui-droid/loom.git /build/loom-src
RUN mkdir -p loom-core-src && cp -R /build/loom-src/loom-core/Cargo.toml /build/loom-src/loom-core/src loom-core-src/
COPY validator/ validator/
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

# Embeddings run in-process via fastembed (ONNX, no PyTorch, no external
# server) — no Ollama, no sidecar, works the same on a free-tier host as
# locally. The first run downloads the ~130MB model from Hugging Face; bake
# it into the image at build time so a cold container doesn't pay for it.
RUN python3 -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5')"

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
