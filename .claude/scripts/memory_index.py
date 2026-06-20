#!/usr/bin/env python3
"""
Vault indexing pipeline — chunks markdown files, embeds them, stores in SQLite.
Incremental by default: only re-indexes files modified since last run.

Usage:
    python memory_index.py           # index changed files only
    python memory_index.py --full    # force full re-index
    python memory_index.py --stats   # show index statistics
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Generator

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from shared import DATA_PATH, VAULT_PATH, atomic_write_json, read_json_safe

INDEX_STATE_PATH = DATA_PATH / "index-state.json"

# Files to skip (identity files loaded via hooks, not worth chunking for search)
SKIP_FILES = {"BOOTSTRAP.md", "HABITS.md"}

# Chunking parameters
CHUNK_WORDS = 400
OVERLAP_WORDS = 50


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, file_path: str) -> list[dict]:
    """
    Split text into overlapping chunks of ~CHUNK_WORDS words.
    Splits on paragraph boundaries first for cleaner semantic units.
    Returns list of {chunk_index, content, char_start, char_end}.
    """
    # Split into paragraphs
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks = []
    current_words: list[str] = []
    current_chars_start = 0
    char_offset = 0

    for para in paragraphs:
        para_words = para.split()
        current_words.extend(para_words)
        char_offset += len(para) + 2  # +2 for \n\n

        if len(current_words) >= CHUNK_WORDS:
            chunk_text_str = " ".join(current_words[:CHUNK_WORDS])
            chunks.append({
                "chunk_index": len(chunks),
                "content": chunk_text_str,
                "char_start": current_chars_start,
                "char_end": current_chars_start + len(chunk_text_str),
            })
            # Keep overlap
            overlap = current_words[CHUNK_WORDS - OVERLAP_WORDS:]
            current_chars_start = char_offset - len(" ".join(overlap))
            current_words = overlap

    # Final partial chunk
    if current_words:
        chunk_text_str = " ".join(current_words)
        if chunk_text_str.strip():
            chunks.append({
                "chunk_index": len(chunks),
                "content": chunk_text_str,
                "char_start": current_chars_start,
                "char_end": current_chars_start + len(chunk_text_str),
            })

    return chunks


# ---------------------------------------------------------------------------
# Incremental state tracking
# ---------------------------------------------------------------------------

def load_index_state() -> dict:
    return read_json_safe(str(INDEX_STATE_PATH), default={})


def save_index_state(state: dict):
    INDEX_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(str(INDEX_STATE_PATH), state)


def get_vault_files() -> list[Path]:
    if not VAULT_PATH.exists():
        return []
    return [
        p for p in VAULT_PATH.rglob("*.md")
        if p.name not in SKIP_FILES
        and ".git" not in p.parts
    ]


def needs_indexing(file_path: Path, state: dict) -> bool:
    key = str(file_path.relative_to(VAULT_PATH))
    recorded_mtime = state.get(key, 0)
    return file_path.stat().st_mtime > recorded_mtime


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------

def index_file(conn, file_path: Path, relative_path: str):
    """Chunk, embed, and store a single file."""
    from db import delete_chunks_for_file, upsert_chunk
    from embeddings import embed_batch

    text = file_path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return 0

    chunks = chunk_text(text, relative_path)
    if not chunks:
        return 0

    # Batch embed all chunks at once
    texts = [c["content"] for c in chunks]
    embeddings = embed_batch(texts)

    # Remove old chunks for this file before inserting new ones
    delete_chunks_for_file(conn, relative_path)

    for chunk, embedding in zip(chunks, embeddings):
        upsert_chunk(
            conn,
            file_path=relative_path,
            chunk_index=chunk["chunk_index"],
            content=chunk["content"],
            embedding=embedding,
            char_start=chunk["char_start"],
            char_end=chunk["char_end"],
        )

    conn.commit()
    return len(chunks)


def run_index(full: bool = False):
    from db import get_connection

    conn = get_connection()
    state = {} if full else load_index_state()
    files = get_vault_files()

    if not files:
        print("No markdown files found in vault.")
        return

    to_index = [f for f in files if full or needs_indexing(f, state)]

    if not to_index:
        print(f"Index is up to date ({len(files)} files, no changes detected).")
        return

    print(f"Indexing {len(to_index)} of {len(files)} files...")
    total_chunks = 0
    errors = 0

    for i, file_path in enumerate(to_index, 1):
        relative = str(file_path.relative_to(VAULT_PATH))
        try:
            n = index_file(conn, file_path, relative)
            total_chunks += n
            state[relative] = file_path.stat().st_mtime
            print(f"  [{i}/{len(to_index)}] {relative} → {n} chunk(s)")
        except Exception as exc:
            print(f"  [{i}/{len(to_index)}] ERROR {relative}: {exc}", file=sys.stderr)
            errors += 1

    save_index_state(state)
    conn.close()

    print(f"\nDone. {total_chunks} chunks indexed across {len(to_index)} files.", end="")
    if errors:
        print(f" ({errors} errors — check stderr for details.)")
    else:
        print()


def show_stats():
    from db import DB_PATH, get_connection

    if not DB_PATH.exists():
        print("No index found. Run: python memory_index.py")
        return

    conn = get_connection()
    n_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    n_files = conn.execute("SELECT COUNT(DISTINCT file_path) FROM chunks").fetchone()[0]
    conn.close()

    state = load_index_state()
    print(f"Index: {n_chunks} chunks across {n_files} files")
    print(f"State: {len(state)} files tracked in {INDEX_STATE_PATH}")
    print(f"DB:    {DB_PATH} ({DB_PATH.stat().st_size // 1024} KB)" if DB_PATH.exists() else "")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index Sintetica vault for hybrid search")
    parser.add_argument("--full", action="store_true", help="Force full re-index")
    parser.add_argument("--stats", action="store_true", help="Show index statistics")
    args = parser.parse_args()

    if args.stats:
        show_stats()
    else:
        run_index(full=args.full)
