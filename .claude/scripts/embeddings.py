"""
FastEmbed wrapper for Sintetica memory search.
Model: BAAI/bge-small-en-v1.5 (384-dim, ONNX, CPU-optimised).
First run downloads ~25 MB model to ~/.cache/fastembed/.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Generator

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
CACHE_DIR = str(Path.home() / ".cache" / "fastembed")

_model = None


def _get_model():
    global _model
    if _model is None:
        try:
            from fastembed import TextEmbedding
        except ImportError:
            raise ImportError(
                "fastembed is not installed. Run: pip install fastembed"
            )
        _model = TextEmbedding(model_name=MODEL_NAME, cache_dir=CACHE_DIR)
    return _model


def embed_batch(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Embed a list of texts. Returns list of 384-dim float vectors."""
    if not texts:
        return []
    model = _get_model()
    results = list(model.embed(texts, batch_size=batch_size))
    return [list(map(float, vec)) for vec in results]


def embed_one(text: str) -> list[float]:
    """Embed a single string."""
    return embed_batch([text])[0]


def vec_to_bytes(vec: list[float]) -> bytes:
    """Serialize a float vector to bytes for sqlite-vec storage."""
    return struct.pack(f"{len(vec)}f", *vec)


def bytes_to_vec(data: bytes) -> list[float]:
    """Deserialize bytes back to a float vector."""
    n = len(data) // 4
    return list(struct.unpack(f"{n}f", data))
