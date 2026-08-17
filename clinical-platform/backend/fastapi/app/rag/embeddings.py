# app/rag/embeddings.py
"""Local embedding using sentence-transformers (small model for demo).

Falls back to a deterministic hash-based pseudo-embedding if the model
can't load (so the demo runs even without ML deps installed).
"""
import os
import hashlib
from typing import List

_DIM = 1536


def _hash_embed(text: str, dim: int = _DIM) -> List[float]:
    """Deterministic pseudo-embedding. NOT semantically meaningful — only used as a fallback."""
    vec = [0.0] * dim
    for i, token in enumerate(text.lower().split()[:dim]):
        h = int(hashlib.sha256(token.encode()).hexdigest()[:8], 16)
        vec[(i + h) % dim] += 1.0 / (1 + i * 0.01)
    norm = sum(x * x for x in vec) ** 0.5
    return [x / norm if norm > 0 else x for x in vec]


_MODEL = None
_MODEL_LOAD_ATTEMPTED = False


def _try_load_model():
    global _MODEL, _MODEL_LOAD_ATTEMPTED
    if _MODEL_LOAD_ATTEMPTED:
        return _MODEL
    _MODEL_LOAD_ATTEMPTED = True
    try:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        _MODEL = None
    return _MODEL


def embed_text(text: str) -> List[float]:
    model = _try_load_model()
    if model is not None:
        try:
            vec = model.encode(text).tolist()
            # Pad / truncate to _DIM
            if len(vec) < _DIM:
                vec = vec + [0.0] * (_DIM - len(vec))
            else:
                vec = vec[:_DIM]
            return vec
        except Exception:
            pass
    return _hash_embed(text)


def embed_texts(texts: List[str]) -> List[List[float]]:
    return [embed_text(t) for t in texts]