# loom-core's source lives in a PRIVATE repo (Munay's own decision — see
# tasks/lessons.md). The validator binary is cross-compiled once locally
# (scripts/build_validator.sh, x86_64-unknown-linux-musl via a musl cross
# toolchain) and committed as validator/prebuilt/loom-validate-linux-x86_64 —
# a compiled artifact, never the source. This means anyone can clone and
# deploy loom-assistant without needing access to the private repo at all.
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ core/
COPY api/ api/
COPY evals/ evals/
COPY validator/prebuilt/loom-validate-linux-x86_64 validator/target/release/loom-validate
RUN chmod +x validator/target/release/loom-validate

# Embeddings run in-process via fastembed (ONNX, no PyTorch, no external
# server) — no Ollama, no sidecar, works the same on a free-tier host as
# locally. The first run downloads the ~130MB model from Hugging Face; bake
# it into the image at build time so a cold container doesn't pay for it.
RUN python3 -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5')"

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
