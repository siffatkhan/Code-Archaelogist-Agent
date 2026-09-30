"""
vector_search.py — similarity search over the `knowledge_embeddings` table.

Owner: M3 (Static Code Intelligence & AI/Knowledge Layer)
Phase: 4 — Retrieval & Embeddings

Given a query vector (produced by `embeddings.embed`), this module finds the
most semantically similar rows already stored in Postgres via pgvector, and
returns them ordered by relevance.

pgvector is the single retrieval mechanism for human knowledge, repository
context, and evidence (per the Database Design doc) — this module never
stands up a parallel vector store (no Chroma, FAISS, or separate SQLite
index). It queries the shared `knowledge_embeddings` table directly:

    knowledge_embeddings: id, repository_id, knowledge_item_id, content,
                          embedding (pgvector), created_at

Distance metric: cosine similarity
-----------------------------------
pgvector supports several operators; this module standardizes on cosine
distance (`<=>`) rather than L2 (`<->`). Reasoning:
  - Cosine similarity measures the *angle* between two vectors — i.e. whether
    they point in the same semantic direction — and ignores magnitude. That's
    the right notion of "similar meaning" for text embeddings, where vector
    length isn't itself meaningful.
  - `embeddings.embed()` already returns L2-normalized vectors, which is
    exactly the precondition cosine similarity assumes, and also makes cosine
    and (normalized) L2 distance monotonically equivalent for ranking — so
    there's no behavioral cost to picking cosine here.
  - pgvector's `<=>` operator returns *cosine distance* (0 = identical,
    2 = opposite). This module converts that to a similarity score in the
    query itself (`1 - distance`) so callers get a score where "higher is
    more similar," matching how similarity is normally reasoned about.

Isolation rule
--------------
Every query is scoped by `repository_id` (per Database Design's isolation
rule) — this module never searches across repositories. It does not itself
verify that the given `repository_id` belongs to the requesting user; that
ownership check happens once, upstream, at the API/service layer that has
the authenticated user's id (this module only receives an already-authorized
`repository_id`).

Integration note
-----------------
This module takes a SQLAlchemy `Session` as a parameter rather than owning
its own DB engine/connection setup — connection/session management (and the
`knowledge_embeddings` ORM model, if one exists) belongs to the shared
`app/models` and `app/core` modules (M1's ownership). Pass in whatever
session your route/service already has.
"""

from __future__ import annotations

from typing import TypedDict

from sqlalchemy import text
from sqlalchemy.orm import Session

from .embeddings import EMBEDDING_DIMENSION


class SearchResult(TypedDict):
    id: str
    knowledge_item_id: str | None
    content: str
    similarity: float


def _vector_literal(embedding: list[float]) -> str:
    """Format a Python list of floats as a pgvector literal, e.g. '[0.1,0.2]'.

    pgvector accepts this bracketed, comma-separated string form when cast
    with `::vector`, which is how we pass a query embedding into SQL without
    needing a custom bind type registered on the engine.
    """
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


def vector_search(
    session: Session,
    repository_id: str,
    query_embedding: list[float],
    top_k: int = 5,
) -> list[SearchResult]:
    """Find the most semantically similar stored items for a query vector.

    Args:
        session: An active SQLAlchemy session/connection to the shared
            Postgres database (with pgvector installed).
        repository_id: UUID of the repository to scope the search to. Must
            already be verified as belonging to the requesting user by the
            caller — this function does not perform that check.
        query_embedding: A vector produced by `embeddings.embed(text)` (or
            `embed_batch`). Must have length EMBEDDING_DIMENSION.
        top_k: Maximum number of results to return, ordered most-similar
            first.

    Returns:
        A list of up to `top_k` results, each with the stored row's id,
        its linked knowledge_item_id (if any), the original content, and a
        cosine similarity score in [-1, 1] (1 = identical direction).

    Raises:
        ValueError: if `query_embedding` isn't the expected dimension.
    """
    if len(query_embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"query_embedding has {len(query_embedding)} dimensions, "
            f"expected {EMBEDDING_DIMENSION}"
        )

    query_vector_literal = _vector_literal(query_embedding)

    sql = text(
        """
        SELECT
            id,
            knowledge_item_id,
            content,
            1 - (embedding <=> CAST(:query_vector AS vector)) AS similarity
        FROM knowledge_embeddings
        WHERE repository_id = :repository_id
        ORDER BY embedding <=> CAST(:query_vector AS vector)
        LIMIT :top_k
        """
    )

    rows = session.execute(
        sql,
        {
            "query_vector": query_vector_literal,
            "repository_id": repository_id,
            "top_k": top_k,
        },
    ).mappings().all()

    return [
        SearchResult(
            id=str(row["id"]),
            knowledge_item_id=str(row["knowledge_item_id"]) if row["knowledge_item_id"] else None,
            content=row["content"],
            similarity=float(row["similarity"]),
        )
        for row in rows
    ]
