"""RAG core for loom-assistant.

Ingests LOOM's own documentation and example patterns (read-only, from
~/Dev/loom), chunks them, embeds them locally via fastembed (ONNX, no
PyTorch, no external server — runs in-process, so it works the same in local
dev and on a small free-tier host, unlike the earlier Ollama-based version
which needed a separate server), and indexes them in Chroma. Retrieval is
hybrid: dense (Chroma) + sparse (BM25), merged by reciprocal rank fusion —
the standard approach cited across the 2026 AI engineering roadmaps as
"hybrid retrieval".

Never writes to ~/Dev/loom. This module only reads from it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import chromadb
from fastembed import TextEmbedding
from rank_bm25 import BM25Okapi

LOOM_REPO = Path.home() / "Dev" / "loom"
# fastembed: ONNX runtime, no PyTorch, ~130MB model. Runs in-process, no
# server to host, no API key — fixes the earlier Ollama problem (a small
# free-tier host can't reliably run a separate Ollama server). Loaded once,
# lazily, on first use.
EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"
CHROMA_DIR = Path(__file__).parent.parent / ".chroma"
COLLECTION_NAME = "loom_docs"

_embedder: TextEmbedding | None = None


def _get_embedder() -> TextEmbedding:
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedding(model_name=EMBED_MODEL_NAME)
    return _embedder

# The docs worth chunking by section. TUTORIEL.md is the main teaching doc;
# README/ROADMAP give project-level context. NIGHT_LOG/PLAN-MONDE are working
# notes, not documentation, so they're excluded on purpose.
DOC_FILES = ["TUTORIEL.md", "README.md", "ROADMAP.md"]


@dataclass
class Chunk:
    id: str
    text: str
    source: str  # relative path, e.g. "TUTORIEL.md#L42" or "additive.loom"


def _chunk_markdown(path: Path) -> list[Chunk]:
    """Split a markdown file on '##'-level headers. Each section becomes one
    chunk; a section header with no body is skipped."""
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"\n(?=##+ )", text)
    chunks = []
    for i, section in enumerate(sections):
        section = section.strip()
        if len(section) < 20:
            continue
        title_match = re.match(r"#+\s*(.+)", section)
        title = title_match.group(1) if title_match else f"section {i}"
        chunks.append(Chunk(id=f"{path.name}::{i}", text=section, source=f"{path.name} — {title}"))
    return chunks


def _chunk_loom_examples() -> list[Chunk]:
    """Each .loom example file is kept as ONE chunk. Splitting a working
    pattern into fragments would lose the coherence that makes it useful as a
    retrieval result (a partial pattern isn't a valid answer to "how do I do
    X in LOOM")."""
    chunks = []
    for f in sorted(LOOM_REPO.glob("*.loom")):
        text = f.read_text(encoding="utf-8")
        if len(text.strip()) < 10:
            continue
        chunks.append(Chunk(id=f"example::{f.stem}", text=text, source=f.name))
    return chunks


def build_corpus() -> list[Chunk]:
    chunks: list[Chunk] = []
    for name in DOC_FILES:
        p = LOOM_REPO / name
        if p.exists():
            chunks.extend(_chunk_markdown(p))
    chunks.extend(_chunk_loom_examples())
    return chunks


EMBED_CHAR_LIMIT = 2000  # bge-small's context window (512 tokens) is small
# enough that a few of the longer .loom examples overflow it. The full chunk
# text is still stored and returned on retrieval; only the *embedding vector*
# is computed from a truncated prefix, which is still representative for a
# language this terse (LOOM patterns front-load the interesting part).


def _embed(texts: list[str]) -> list[list[float]]:
    vectors = _get_embedder().embed([t[:EMBED_CHAR_LIMIT] for t in texts])
    return [v.tolist() for v in vectors]


def index_corpus(chunks: list[Chunk] | None = None) -> None:
    """(Re)build the Chroma index from scratch. Idempotent: deletes and
    recreates the collection each time, so re-running after editing LOOM's
    docs always reflects the current state."""
    chunks = chunks or build_corpus()
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)
    embeddings = _embed([c.text for c in chunks])
    collection.add(
        ids=[c.id for c in chunks],
        documents=[c.text for c in chunks],
        embeddings=embeddings,
        metadatas=[{"source": c.source} for c in chunks],
    )


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z_]+", text.lower())


class HybridRetriever:
    """Dense (Chroma/fastembed) + sparse (BM25) retrieval, merged by
    reciprocal rank fusion (k=60, the standard constant from the original RRF
    paper). Loads the corpus into memory once at construction time."""

    def __init__(self) -> None:
        self.chunks = build_corpus()
        self._by_id = {c.id: c for c in self.chunks}
        self._bm25 = BM25Okapi([_tokenize(c.text) for c in self.chunks])
        self._client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._collection = self._client.get_or_create_collection(COLLECTION_NAME)

    def retrieve(self, query: str, k: int = 4) -> list[Chunk]:
        # Dense side.
        q_emb = next(_get_embedder().embed([query])).tolist()
        dense = self._collection.query(query_embeddings=[q_emb], n_results=min(20, len(self.chunks)))
        dense_ids = dense["ids"][0]

        # Sparse side.
        scores = self._bm25.get_scores(_tokenize(query))
        ranked_sparse = sorted(range(len(self.chunks)), key=lambda i: scores[i], reverse=True)
        sparse_ids = [self.chunks[i].id for i in ranked_sparse[:20]]

        # Reciprocal rank fusion.
        rrf: dict[str, float] = {}
        for rank, cid in enumerate(dense_ids):
            rrf[cid] = rrf.get(cid, 0.0) + 1.0 / (60 + rank)
        for rank, cid in enumerate(sparse_ids):
            rrf[cid] = rrf.get(cid, 0.0) + 1.0 / (60 + rank)

        top = sorted(rrf.items(), key=lambda kv: kv[1], reverse=True)[:k]
        return [self._by_id[cid] for cid, _ in top]


if __name__ == "__main__":
    print("Indexing LOOM corpus...")
    corpus = build_corpus()
    print(f"{len(corpus)} chunks ({sum(1 for c in corpus if c.id.startswith('example::'))} examples, "
          f"{sum(1 for c in corpus if not c.id.startswith('example::'))} doc sections)")
    index_corpus(corpus)
    print("Indexed. Try: python -m core.rag_query 'how do I make a euclidean kick pattern'")
