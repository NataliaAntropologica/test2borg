"""
SQLite abstraction for Sintetica memory search.
- FTS5 for keyword search (built-in to SQLite, no extension needed)
- Embeddings stored as BLOB in SQLite; numpy used for in-memory vector search

Install: pip install numpy fastembed
"""

from __future__ import annotations

import json
import sqlite3
import struct
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent.parent / "data" / "memory.db"


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open (or create) the memory database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection):
    # Standalone FTS5 (no content-table link) — stores its own copy of content.
    # Simpler and more reliable than content-table mode; slight storage duplication
    # is acceptable for a personal vault.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path   TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content     TEXT NOT NULL,
            embedding   BLOB,
            char_start  INTEGER DEFAULT 0,
            char_end    INTEGER DEFAULT 0,
            UNIQUE(file_path, chunk_index)
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS fts_chunks
        USING fts5(content, tokenize='porter ascii')
    """)
    conn.commit()


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def upsert_chunk(
    conn: sqlite3.Connection,
    file_path: str,
    chunk_index: int,
    content: str,
    embedding: list[float],
    char_start: int = 0,
    char_end: int = 0,
) -> int:
    """Insert or replace a chunk and its embedding. Returns the chunk id."""
    emb_blob = struct.pack(f"{len(embedding)}f", *embedding)

    conn.execute(
        """
        INSERT INTO chunks (file_path, chunk_index, content, embedding, char_start, char_end)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(file_path, chunk_index) DO UPDATE SET
            content=excluded.content,
            embedding=excluded.embedding,
            char_start=excluded.char_start,
            char_end=excluded.char_end
        """,
        (file_path, chunk_index, content, emb_blob, char_start, char_end),
    )
    row = conn.execute(
        "SELECT id FROM chunks WHERE file_path=? AND chunk_index=?",
        (file_path, chunk_index),
    ).fetchone()
    chunk_id = row["id"]

    # Rebuild FTS entry — delete old entry (if any) then insert fresh
    try:
        conn.execute(
            "INSERT INTO fts_chunks(fts_chunks, rowid, content) VALUES ('delete', ?, ?)",
            (chunk_id, content),
        )
    except Exception:
        pass  # row not in FTS yet (first insert) — safe to ignore
    conn.execute(
        "INSERT INTO fts_chunks(rowid, content) VALUES (?, ?)",
        (chunk_id, content),
    )
    return chunk_id


def delete_chunks_for_file(conn: sqlite3.Connection, file_path: str):
    """Remove all chunks belonging to a file."""
    rows = conn.execute(
        "SELECT id, content FROM chunks WHERE file_path=?", (file_path,)
    ).fetchall()
    for r in rows:
        # FTS5 standalone delete requires the original content
        try:
            conn.execute(
                "INSERT INTO fts_chunks(fts_chunks, rowid, content) VALUES ('delete', ?, ?)",
                (r["id"], r["content"]),
            )
        except Exception:
            pass  # ignore if row doesn't exist in FTS
    conn.execute("DELETE FROM chunks WHERE file_path=?", (file_path,))


# ---------------------------------------------------------------------------
# Vector search (numpy cosine similarity, in-memory)
# ---------------------------------------------------------------------------

def vector_search(
    conn: sqlite3.Connection,
    query_embedding: list[float],
    top_k: int = 20,
    path_prefix: Optional[str] = None,
) -> list[dict]:
    """Return top-k chunks by cosine similarity using numpy."""
    import numpy as np

    sql = "SELECT id, file_path, chunk_index, content, embedding FROM chunks WHERE embedding IS NOT NULL"
    params = []
    if path_prefix:
        sql += " AND file_path LIKE ?"
        params.append(f"%{path_prefix}%")

    rows = conn.execute(sql, params).fetchall()
    if not rows:
        return []

    dim = len(query_embedding)
    q = np.array(query_embedding, dtype=np.float32)
    q_norm = q / (np.linalg.norm(q) + 1e-10)

    ids, file_paths, chunk_indexes, contents, similarities = [], [], [], [], []
    for row in rows:
        blob = row["embedding"]
        n = len(blob) // 4
        vec = np.array(struct.unpack(f"{n}f", blob), dtype=np.float32)
        norm = np.linalg.norm(vec)
        sim = float(np.dot(q_norm, vec / (norm + 1e-10)))
        ids.append(row["id"])
        file_paths.append(row["file_path"])
        chunk_indexes.append(row["chunk_index"])
        contents.append(row["content"])
        similarities.append(sim)

    # Sort descending by similarity, take top_k
    ranked = sorted(zip(similarities, ids, file_paths, chunk_indexes, contents), reverse=True)
    results = []
    for sim, cid, fp, ci, ct in ranked[:top_k]:
        results.append({
            "id": cid,
            "file_path": fp,
            "chunk_index": ci,
            "content": ct,
            "distance": 1.0 - sim,  # convert to distance for hybrid_merge compatibility
        })
    return results


# ---------------------------------------------------------------------------
# Keyword search (FTS5 BM25)
# ---------------------------------------------------------------------------

def keyword_search(
    conn: sqlite3.Connection,
    query: str,
    top_k: int = 20,
    path_prefix: Optional[str] = None,
) -> list[dict]:
    """Return top-k chunks by FTS5 BM25 rank."""
    prefix_filter = "AND c.file_path LIKE ?" if path_prefix else ""
    params: list = [query, top_k]
    if path_prefix:
        params.insert(1, f"%{path_prefix}%")

    sql = f"""
        SELECT c.id, c.file_path, c.chunk_index, c.content, f.rank
        FROM fts_chunks f
        JOIN chunks c ON c.id = f.rowid
        WHERE fts_chunks MATCH ?
          {prefix_filter}
        ORDER BY f.rank
        LIMIT ?
    """
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError:
        return []
