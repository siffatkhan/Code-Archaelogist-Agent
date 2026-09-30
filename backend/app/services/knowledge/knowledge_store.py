"""
knowledge_store.py — CRUD for human-provided knowledge (`knowledge_items`),
the write side of `knowledge_embeddings`, and linking resolved gaps back to
the knowledge item that resolved them.

Owner: M3 (Static Code Intelligence & AI/Knowledge Layer)
Phase: 5 — Knowledge Store & Gap Detection

Responsibilities:
  - Save a new knowledge item (title, content, source) for a repository.
  - Fetch reusable knowledge items for a repository.
  - Resolve a knowledge gap: create the `knowledge_items` row for the human's
    answer AND write its id into `knowledge_gaps.resolved_knowledge_item_id`,
    so the original question stays linked to what resolved it.

Every knowledge item saved here is also embedded (via Phase 4's `embed()`)
and stored in `knowledge_embeddings` with `knowledge_item_id` set, so it's
immediately retrievable through Phase 4's `vector_search` — this is what
lets a past human answer surface as evidence for a future, similar question.

Integration notes
------------------
- These functions take a SQLAlchemy `Session` rather than owning connection
  setup (that's M1's `app/core`), matching the pattern from Phase 4.
- None of these functions call `session.commit()` — they use `session.flush()`
  only, so the caller's request-scoped session controls the transaction
  boundary (standard FastAPI session-per-request pattern). Call
  `session.commit()` after, at whatever layer owns the transaction.
- Ownership/isolation: per Database Design, every repository-scoped query is
  checked against the owning user upstream (at the API/service layer that
  has the authenticated user's id). These functions accept an already
  authorized `repository_id` and do not themselves re-verify user ownership.
- `evidence` rows (linking a knowledge item to a future cited answer) are
  built by the Historian agent later, not here — this module only writes
  `knowledge_items` and `knowledge_embeddings`.
"""

from __future__ import annotations

from typing import Optional, TypedDict

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..retrieval.embeddings import embed


class KnowledgeItem(TypedDict):
    id: str
    repository_id: str
    user_id: Optional[str]
    title: str
    content: str
    source: str
    created_at: str
    updated_at: str


class KnowledgeGap(TypedDict):
    id: str
    repository_id: str
    question: str
    context: Optional[str]
    priority: str
    status: str
    resolved_knowledge_item_id: Optional[str]
    created_at: str
    resolved_at: Optional[str]


def _vector_literal(embedding: list[float]) -> str:
    """Format a Python list of floats as a pgvector literal string, e.g.
    '[0.1,0.2]'. Kept local to this module (small, self-contained utility)
    rather than importing a private helper out of `vector_search.py`.
    """
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


def _row_to_knowledge_item(row) -> KnowledgeItem:
    return KnowledgeItem(
        id=str(row["id"]),
        repository_id=str(row["repository_id"]),
        user_id=str(row["user_id"]) if row["user_id"] else None,
        title=row["title"],
        content=row["content"],
        source=row["source"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _row_to_gap(row) -> KnowledgeGap:
    return KnowledgeGap(
        id=str(row["id"]),
        repository_id=str(row["repository_id"]),
        question=row["question"],
        context=row["context"],
        priority=row["priority"],
        status=row["status"],
        resolved_knowledge_item_id=(
            str(row["resolved_knowledge_item_id"]) if row["resolved_knowledge_item_id"] else None
        ),
        created_at=str(row["created_at"]),
        resolved_at=str(row["resolved_at"]) if row["resolved_at"] else None,
    )


def save_knowledge_item(
    session: Session,
    repository_id: str,
    title: str,
    content: str,
    source: str,
    user_id: Optional[str] = None,
) -> KnowledgeItem:
    """Save a new human-provided knowledge item and index it for retrieval.

    Inserts into `knowledge_items`, then embeds `content` via Phase 4's
    `embed()` and inserts a matching row into `knowledge_embeddings` with
    `knowledge_item_id` pointing back at the new item — this is what makes
    the item show up in `vector_search` results afterwards.

    Args:
        session: Active SQLAlchemy session (not committed by this function).
        repository_id: Repository this knowledge belongs to (already
            authorized by the caller).
        title: Short label for the knowledge item.
        content: The actual explanation/knowledge text. This is what gets
            embedded and what future searches match against.
        source: Where this knowledge came from, e.g. "manual", "gap_answer".
        user_id: The user who supplied this knowledge, if known.

    Returns:
        The newly created knowledge item.
    """
    item_row = session.execute(
        text(
            """
            INSERT INTO knowledge_items (repository_id, user_id, title, content, source)
            VALUES (:repository_id, :user_id, :title, :content, :source)
            RETURNING id, repository_id, user_id, title, content, source, created_at, updated_at
            """
        ),
        {
            "repository_id": repository_id,
            "user_id": user_id,
            "title": title,
            "content": content,
            "source": source,
        },
    ).mappings().one()

    knowledge_item = _row_to_knowledge_item(item_row)

    embedding = embed(content)
    session.execute(
        text(
            """
            INSERT INTO knowledge_embeddings (repository_id, knowledge_item_id, content, embedding)
            VALUES (:repository_id, :knowledge_item_id, :content, CAST(:embedding AS vector))
            """
        ),
        {
            "repository_id": repository_id,
            "knowledge_item_id": knowledge_item["id"],
            "content": content,
            "embedding": _vector_literal(embedding),
        },
    )

    session.flush()
    return knowledge_item


def get_knowledge_items(session: Session, repository_id: str) -> list[KnowledgeItem]:
    """Fetch all reusable knowledge items for a repository, newest first.

    Powers `GET /repositories/{repository_id}/knowledge` (evidence assembly
    for that endpoint's response is the Historian agent's job, not this
    function's — this just returns the knowledge items themselves).
    """
    rows = session.execute(
        text(
            """
            SELECT id, repository_id, user_id, title, content, source, created_at, updated_at
            FROM knowledge_items
            WHERE repository_id = :repository_id
            ORDER BY created_at DESC
            """
        ),
        {"repository_id": repository_id},
    ).mappings().all()

    return [_row_to_knowledge_item(row) for row in rows]


def resolve_knowledge_gap(
    session: Session,
    repository_id: str,
    gap_id: str,
    answer: str,
    user_id: Optional[str] = None,
    title: Optional[str] = None,
) -> KnowledgeItem:
    """Resolve a knowledge gap with a human-provided answer.

    Powers `POST /repositories/{repository_id}/knowledge-gaps/{gap_id}/answer`.
    Creates the `knowledge_items` row for the answer (embedding it via
    `save_knowledge_item`, so it's retrievable for future questions), then
    links it back by setting `knowledge_gaps.resolved_knowledge_item_id` and
    marking the gap `status = 'resolved'` with a `resolved_at` timestamp —
    keeping the original question connected to what resolved it.

    Args:
        session: Active SQLAlchemy session (not committed by this function).
        repository_id: Repository the gap belongs to (already authorized).
        gap_id: The `knowledge_gaps.id` being resolved.
        answer: The human-provided explanation text.
        user_id: The user providing the answer, if known.
        title: Optional short label for the resulting knowledge item;
            defaults to the gap's original question, truncated.

    Returns:
        The newly created knowledge item that resolved the gap.

    Raises:
        ValueError: if no gap with `gap_id` exists for `repository_id` (also
            enforces the isolation rule — a gap from another repository
            can't be resolved through this call).
    """
    gap_row = session.execute(
        text(
            """
            SELECT id, question
            FROM knowledge_gaps
            WHERE id = :gap_id AND repository_id = :repository_id
            """
        ),
        {"gap_id": gap_id, "repository_id": repository_id},
    ).mappings().first()

    if gap_row is None:
        raise ValueError(
            f"No knowledge gap {gap_id!r} found for repository {repository_id!r}"
        )

    resolved_title = title or (gap_row["question"][:120])

    knowledge_item = save_knowledge_item(
        session,
        repository_id=repository_id,
        title=resolved_title,
        content=answer,
        source="gap_answer",
        user_id=user_id,
    )

    session.execute(
        text(
            """
            UPDATE knowledge_gaps
            SET resolved_knowledge_item_id = :knowledge_item_id,
                status = 'resolved',
                resolved_at = now()
            WHERE id = :gap_id AND repository_id = :repository_id
            """
        ),
        {
            "knowledge_item_id": knowledge_item["id"],
            "gap_id": gap_id,
            "repository_id": repository_id,
        },
    )

    session.flush()
    return knowledge_item
