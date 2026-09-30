"""
gap_detector.py — decides when the available evidence is NOT enough to
answer a question confidently, and creates `knowledge_gaps` rows when that
happens.

Owner: M3 (Static Code Intelligence & AI/Knowledge Layer)
Phase: 5 — Knowledge Store & Gap Detection

Detection strategy
-------------------
This module's own responsibility is the deterministic, retrieval-based half
of gap detection: it embeds the question (Phase 4's `embed()`) and checks
how strong the best available match is (Phase 4's `vector_search()`). A gap
is flagged when:

  1. Retrieval returns nothing at all for the question (empty result), or
  2. The best match's similarity score falls below SIMILARITY_THRESHOLD.

The spec's third trigger — "a question requires reasoning about intent/
history the repository's static content genuinely doesn't capture" — isn't
something a similarity score alone can decide; it needs judgment about what
the question is actually asking, which is the Historian/Knowledge Gap
agent's job (a later phase, once the LLM is wired into the graph). This
module exposes a `requires_human_judgment` override parameter so that agent
can force a gap even when retrieval alone looks sufficient, without this
module needing to make LLM calls itself. Flagging this explicitly rather
than quietly deciding it either way, per the "stop and report conflicts"
rule — this is a scope boundary, not a silent scope change: worth confirming
this split matches your intent before Phase 6/7 build on it.

Threshold
---------
SIMILARITY_THRESHOLD = 0.35 (cosine similarity, matching Phase 4's scale,
where 1.0 = identical direction and 0.0 = unrelated). This is an empirical
starting point for `all-MiniLM-L6-v2`-style sentence embeddings, where
genuinely relevant matches typically score well above 0.4 and unrelated
content typically sits below 0.2-0.3 — 0.35 sits in between, biased slightly
toward flagging a gap when in doubt (a human reviewing an unnecessary gap
costs little; a silently wrong "confident" answer costs more). Tune this
constant based on real repository data once available; if Phase 4's
fallback (non-model) embedder is active, its similarity scores run on a
different scale and this threshold may need separate calibration — see
Phase 4's `embeddings.py` for that fallback's conditions.

Priority heuristic
------------------
  - No matches at all found                      -> "high"
  - Best match similarity < SIMILARITY_THRESHOLD/2 -> "high"
  - Best match similarity < SIMILARITY_THRESHOLD    -> "medium"
  - Forced via `requires_human_judgment` alone      -> "medium"
    (retrieval found something plausible, it's the framing that's the gap)
A caller can always override with an explicit `priority`.
"""

from __future__ import annotations

from typing import Optional, TypedDict

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..retrieval.embeddings import embed
from ..retrieval.vector_search import vector_search

SIMILARITY_THRESHOLD = 0.35


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


def _create_gap(
    session: Session,
    repository_id: str,
    question: str,
    context: Optional[str],
    priority: str,
) -> KnowledgeGap:
    row = session.execute(
        text(
            """
            INSERT INTO knowledge_gaps (repository_id, question, context, priority, status)
            VALUES (:repository_id, :question, :context, :priority, 'open')
            RETURNING id, repository_id, question, context, priority, status,
                      resolved_knowledge_item_id, created_at, resolved_at
            """
        ),
        {
            "repository_id": repository_id,
            "question": question,
            "context": context,
            "priority": priority,
        },
    ).mappings().one()
    session.flush()
    return _row_to_gap(row)


def detect_gap(
    session: Session,
    repository_id: str,
    question: str,
    context: Optional[str] = None,
    requires_human_judgment: bool = False,
    priority: Optional[str] = None,
    similarity_threshold: float = SIMILARITY_THRESHOLD,
) -> Optional[KnowledgeGap]:
    """Check whether a question has strong enough evidence; create a
    `knowledge_gaps` row if it doesn't.

    Args:
        session: Active SQLAlchemy session (not committed by this function;
            see Phase 4/knowledge_store.py for the same convention).
        repository_id: Repository to scope the evidence search to (already
            authorized by the caller).
        question: The question being asked.
        context: Optional extra context to store alongside the gap (e.g. the
            conversation or code location that prompted the question).
        requires_human_judgment: Set by an upstream agent that has already
            determined (via the LLM) that this question needs human intent/
            history the repository's static content doesn't capture, even if
            retrieval alone looks sufficient. See module docstring.
        priority: Explicit priority override ("low"/"medium"/"high"); if
            omitted, one is derived from the retrieval score.
        similarity_threshold: Cosine similarity cutoff below which the best
            match is considered insufficient. Defaults to
            SIMILARITY_THRESHOLD.

    Returns:
        The newly created knowledge gap if one was flagged, else None (the
        existing evidence was strong enough — no gap needed).
    """
    query_vector = embed(question)
    results = vector_search(session, repository_id, query_vector, top_k=1)
    best_similarity = results[0]["similarity"] if results else None

    is_gap = (
        requires_human_judgment
        or best_similarity is None
        or best_similarity < similarity_threshold
    )

    if not is_gap:
        return None

    if priority is None:
        if best_similarity is None:
            priority = "high"
        elif best_similarity < similarity_threshold / 2:
            priority = "high"
        elif not requires_human_judgment:
            priority = "medium"
        else:
            priority = "medium"

    return _create_gap(session, repository_id, question, context, priority)


def list_knowledge_gaps(
    session: Session,
    repository_id: str,
    status: Optional[str] = None,
) -> list[KnowledgeGap]:
    """Fetch knowledge gaps for a repository, optionally filtered by status
    (e.g. "open", "resolved"). Powers
    `GET /repositories/{repository_id}/knowledge-gaps`.
    """
    if status is not None:
        rows = session.execute(
            text(
                """
                SELECT id, repository_id, question, context, priority, status,
                       resolved_knowledge_item_id, created_at, resolved_at
                FROM knowledge_gaps
                WHERE repository_id = :repository_id AND status = :status
                ORDER BY created_at DESC
                """
            ),
            {"repository_id": repository_id, "status": status},
        ).mappings().all()
    else:
        rows = session.execute(
            text(
                """
                SELECT id, repository_id, question, context, priority, status,
                       resolved_knowledge_item_id, created_at, resolved_at
                FROM knowledge_gaps
                WHERE repository_id = :repository_id
                ORDER BY created_at DESC
                """
            ),
            {"repository_id": repository_id},
        ).mappings().all()

    return [_row_to_gap(row) for row in rows]
