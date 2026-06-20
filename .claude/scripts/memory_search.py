#!/usr/bin/env python3
"""
Hybrid memory search — combines vector similarity (0.7) and BM25 keyword (0.3)
via Reciprocal Rank Fusion. Run this to query the Sintetica vault.

Usage:
    python memory_search.py "what patterns repeat across strategy clients"
    python memory_search.py "AI policy signals" --top-k 5
    python memory_search.py "follow up on proposal" --path-prefix drafts/sent
    python memory_search.py "client preferences" --path-prefix clients
    python memory_search.py --index-first "strategic decisions 2026"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(Path(__file__).parent))


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------

RRF_K = 60  # standard constant; higher = smoother rank weighting


def rrf_score(rank: int) -> float:
    return 1.0 / (RRF_K + rank)


def hybrid_merge(
    vec_results: list[dict],
    kw_results: list[dict],
    vec_weight: float = 0.7,
    kw_weight: float = 0.3,
    top_k: int = 10,
) -> list[dict]:
    """
    Merge vector and keyword result sets using weighted RRF.
    Returns top_k results with combined scores, deduped by chunk id.
    """
    scores: dict[int, float] = {}
    meta: dict[int, dict] = {}

    for rank, r in enumerate(vec_results):
        cid = r["id"]
        scores[cid] = scores.get(cid, 0.0) + vec_weight * rrf_score(rank + 1)
        meta[cid] = r

    for rank, r in enumerate(kw_results):
        cid = r["id"]
        scores[cid] = scores.get(cid, 0.0) + kw_weight * rrf_score(rank + 1)
        if cid not in meta:
            meta[cid] = r

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    results = []
    for cid, score in ranked:
        entry = dict(meta[cid])
        entry["score"] = round(score, 4)
        entry.pop("distance", None)
        entry.pop("rank", None)
        results.append(entry)

    return results


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def search(
    query: str,
    top_k: int = 10,
    path_prefix: Optional[str] = None,
) -> list[dict]:
    from db import get_connection, keyword_search, vector_search
    from embeddings import embed_one

    conn = get_connection()
    query_vec = embed_one(query)

    vec_results = vector_search(conn, query_vec, top_k=top_k * 2, path_prefix=path_prefix)
    kw_results = keyword_search(conn, query, top_k=top_k * 2, path_prefix=path_prefix)
    conn.close()

    return hybrid_merge(vec_results, kw_results, top_k=top_k)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_results(results: list[dict], query: str) -> str:
    if not results:
        return f'No results found for "{query}".'

    lines = [f'Search: "{query}"  ({len(results)} result(s))\n']
    for i, r in enumerate(results, 1):
        file_path = r.get("file_path", "")
        score = r.get("score", 0)
        content = r.get("content", "").strip()
        # Truncate long chunks for display
        preview = content[:400] + "…" if len(content) > 400 else content
        lines.append(f"[{i}] {file_path}  (score: {score})")
        lines.append(f"    {preview.replace(chr(10), ' ')}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Hybrid semantic + keyword search over the Sintetica vault"
    )
    parser.add_argument("query", help="Search query")
    parser.add_argument("--top-k", type=int, default=10, help="Number of results (default: 10)")
    parser.add_argument(
        "--path-prefix",
        default=None,
        help="Restrict search to files under this path prefix (e.g. drafts/sent, clients)",
    )
    parser.add_argument(
        "--index-first",
        action="store_true",
        help="Run the indexer on changed files before searching",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    if args.index_first:
        import memory_index
        memory_index.run_index(full=False)
        print()

    try:
        results = search(args.query, top_k=args.top_k, path_prefix=args.path_prefix)
    except ImportError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print("Install dependencies: pip install fastembed sqlite-vec", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Search error: {exc}", file=sys.stderr)
        print("Has the vault been indexed? Run: python memory_index.py", file=sys.stderr)
        sys.exit(1)

    if args.json:
        import json
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(format_results(results, args.query))
