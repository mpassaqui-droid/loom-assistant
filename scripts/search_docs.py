#!/usr/bin/env python3
"""CLI wrapper around HybridRetriever, so `claude -p` (via its Bash tool) can
search LOOM's docs without needing the Anthropic tool_use protocol. Usage:

    python3 scripts/search_docs.py "how do I make a euclidean kick pattern"
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.rag import HybridRetriever

if __name__ == "__main__":
    query = " ".join(sys.argv[1:])
    if not query:
        print("usage: search_docs.py <query>", file=sys.stderr)
        sys.exit(1)
    retriever = HybridRetriever()
    for chunk in retriever.retrieve(query, k=4):
        print(f"=== {chunk.source} ===")
        print(chunk.text)
        print()
