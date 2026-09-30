"""
embeddings.py — turns text into fixed-length vectors for semantic similarity search.

Owner: M3 (Static Code Intelligence & AI/Knowledge Layer)
Phase: 4 — Retrieval & Embeddings

This module is pure "text -> vector" infrastructure. It does not call an LLM,
does not talk to the database, and does not know about repositories, knowledge
items, or the API layer. `vector_search.py` and (later) `knowledge_store.py`
are the callers.

Model choice
------------
Groq's hosted API is inference-only (chat/completions style endpoints for
models like Llama and Whisper) — it does not expose an embeddings endpoint.
So this module embeds text locally using `sentence-transformers` with the
`all-MiniLM-L6-v2` model:
  - free (no per-call API key, no rate limit, no usage cost)
  - small and fast enough to run on CPU, which fits a free-tier hackathon build
  - produces 384-dimensional vectors, which is what `knowledge_embeddings.embedding`
    is sized for (see EMBEDDING_DIMENSION below — keep the pgvector column
    dimension in the DB migration in sync with this constant)

All vectors are L2-normalized before being returned, which is what makes
cosine similarity (used in vector_search.py) meaningful and cheap to compute.

Offline fallback
-----------------
If the model can't be loaded (e.g. no internet access to download model
weights on a fresh machine), this module falls back to a deterministic local
embedder so the rest of the pipeline (storage, similarity search, tests)
keeps working end-to-end. The fallback is intentionally simple — hashed,
weighted bag-of-words — and is meaningfully lower quality than the real model
(keyword overlap rather than deep semantic meaning). It exists purely for
resilience during development/demos, not as an intended production path.
Either backend returns vectors of the same fixed dimension, so callers never
need to know which one is active.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# Must match the pgvector column dimension for knowledge_embeddings.embedding.
EMBEDDING_DIMENSION = 384

_MODEL_NAME = "all-MiniLM-L6-v2"

_model_lock = threading.Lock()
_model = None  # lazily-loaded SentenceTransformer instance
_model_load_failed = False


def _load_model():
    """Lazily load and cache the sentence-transformers model (thread-safe).

    Returns the loaded model, or None if loading failed (network/disk issue),
    in which case callers should use the local fallback embedder instead.
    """
    global _model, _model_load_failed

    if _model is not None or _model_load_failed:
        return _model

    with _model_lock:
        if _model is not None or _model_load_failed:
            return _model
        try:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(_MODEL_NAME)
            logger.info("Loaded embedding model '%s' (dim=%d)", _MODEL_NAME, EMBEDDING_DIMENSION)
        except Exception as exc:  # noqa: BLE001 - any load failure -> fallback
            _model_load_failed = True
            logger.warning(
                "Could not load sentence-transformers model '%s' (%s). "
                "Falling back to local hashed embeddings — quality will be lower.",
                _MODEL_NAME,
                exc,
            )
    return _model


_TOKEN_RE = re.compile(r"[a-z0-9]+")
_NGRAM_SIZE = 3


def _fallback_embed(text: str) -> list[float]:
    """Deterministic, dependency-free embedding used only if the real model
    is unavailable. Hashes character n-grams (not whole words) into one of
    EMBEDDING_DIMENSION buckets, then L2-normalizes the result.

    Character n-grams rather than whole-word hashing on purpose: they give
    partial credit between related word forms that share substrings (e.g.
    "authentication" and "auth" share trigrams like "aut"/"uth"), so this
    fallback still does reasonably at matching a query to related stored
    content even without any real semantic model — it's lexical overlap, not
    a synonym-aware embedding, but it degrades gracefully rather than
    matching nothing.
    """
    vector = [0.0] * EMBEDDING_DIMENSION
    words = _TOKEN_RE.findall(text.lower())

    if not words:
        return vector

    for word in words:
        padded = f"^{word}$"
        ngrams = (
            [padded[i : i + _NGRAM_SIZE] for i in range(len(padded) - _NGRAM_SIZE + 1)]
            if len(padded) >= _NGRAM_SIZE
            else [padded]
        )
        for ngram in ngrams:
            digest = hashlib.sha256(ngram.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSION
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign

    return _normalize(vector)


def _normalize(vector: list[float]) -> list[float]:
    """L2-normalize a vector; returns the zero vector unchanged."""
    norm = math.sqrt(sum(component * component for component in vector))
    if norm == 0.0:
        return vector
    return [component / norm for component in vector]


def embed(text: str) -> list[float]:
    """Embed a single piece of text into a fixed-length vector.

    Works for any short-to-medium text: a knowledge item, a commit message,
    a code snippet/docstring, or a user's question — the same function is
    used for both what gets stored and what gets searched, which is required
    for the vectors to be comparable.

    Args:
        text: The text to embed. Empty/whitespace-only text still returns a
            valid EMBEDDING_DIMENSION-length vector (all zeros).

    Returns:
        A list of EMBEDDING_DIMENSION floats, L2-normalized.
    """
    if text is None:
        text = ""

    model = _load_model()
    if model is not None:
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    return _fallback_embed(text)


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts at once. Equivalent to calling `embed` on each
    item, but batches the call to the model for efficiency when the real
    model backend is active.

    Args:
        texts: List of texts to embed.

    Returns:
        A list of embedding vectors, in the same order as `texts`.
    """
    if not texts:
        return []

    model = _load_model()
    if model is not None:
        vectors = model.encode(list(texts), normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    return [_fallback_embed(t) for t in texts]


def get_embedding_dimension() -> int:
    """Returns the fixed vector length this module always produces. Use this
    instead of hard-coding 384 elsewhere, so the pgvector column and any
    validation stay in sync with whatever this module actually returns.
    """
    return EMBEDDING_DIMENSION


if __name__ == "__main__":
    # Quick manual smoke test: run `python embeddings.py`.
    logging.basicConfig(level=logging.INFO)
    samples = [
        "User authentication and login logic",
        "CSS styling for the navbar",
    ]
    vectors = embed_batch(samples)
    for sample, vector in zip(samples, vectors):
        print(f"{sample!r} -> dim={len(vector)} first 5={vector[:5]}")
