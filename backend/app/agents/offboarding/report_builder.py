"""
report_builder.py — assembles an offboarding session's questions, the risk
areas they target, and (once answered) the knowledge-transfer results into
the final report shape.

Owner: M3 (Static Code Intelligence & AI/Knowledge Layer)
Phase: 8 — Offboarding (capstone)

Powers `GET /repositories/{repository_id}/offboarding/{session_id}`. The
API Contract describes this endpoint's content ("session questions, risk
areas, and knowledge-transfer results") without pinning down an exact JSON
shape the way `/questions` and `/guidance` are pinned down — so the shape
below is this module's own reasonable design, documented clearly in case
M1's response model expects different field names.

Answer submission
------------------
The phase spec notes offboarding answers should become `knowledge_items`
"just like a regular knowledge-gap answer," but no endpoint for *submitting*
an answer appears in the API Contract excerpt this phase was given — only
`POST .../offboarding` (create session) and `GET .../offboarding/{id}`
(read report). `record_answer` below is this module's addition to make that
capability actually available for M1 to wire up (its own route, if the full
contract has one elsewhere) — flagging it as an addition beyond what was
explicitly specified, rather than silently assuming no such endpoint is
needed.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import text

from ...services.knowledge.knowledge_store import save_knowledge_item


def _row_to_question(row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "question": row["question"],
        "priority": row["priority"],
        "answer": row["answer"],
        "status": row["status"],
    }


def build_report(session, repository_id: str, session_id: str) -> dict[str, Any]:
    """Assemble the full offboarding report for a session.

    Args:
        session: Active SQLAlchemy session.
        repository_id: Already-authorized repository id (used to verify the
            session actually belongs to this repository — the isolation
            rule applies here too, not just to knowledge/questions).
        session_id: The `offboarding_sessions.id` to report on.

    Returns:
        {
          "session_id": str,
          "contributor": {"id": str, "name": str, "external_id": str},
          "status": str,
          "created_at": str,
          "completed_at": str | None,
          "questions": [
            {"id", "question", "priority", "answer", "status",
             "risk_area": {"file_path", "score", "explanation"} | None}
          ],
        }

    Raises:
        ValueError: if no session with `session_id` exists for
            `repository_id`.
    """
    session_row = session.execute(
        text(
            """
            SELECT os.id, os.repository_id, os.status, os.created_at, os.completed_at,
                   c.id AS contributor_id, c.name AS contributor_name, c.external_id
            FROM offboarding_sessions os
            JOIN contributors c ON c.id = os.contributor_id
            WHERE os.id = :session_id AND os.repository_id = :repository_id
            """
        ),
        {"session_id": session_id, "repository_id": repository_id},
    ).mappings().first()

    if session_row is None:
        raise ValueError(
            f"No offboarding session {session_id!r} found for repository {repository_id!r}"
        )

    question_rows = session.execute(
        text(
            """
            SELECT id, question, priority, answer, status
            FROM offboarding_questions
            WHERE session_id = :session_id
            ORDER BY
                CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                id
            """
        ),
        {"session_id": session_id},
    ).mappings().all()

    questions = [_row_to_question(row) for row in question_rows]

    return {
        "session_id": str(session_row["id"]),
        "contributor": {
            "id": str(session_row["contributor_id"]),
            "name": session_row["contributor_name"],
            "external_id": session_row["external_id"],
        },
        "status": session_row["status"],
        "created_at": str(session_row["created_at"]),
        "completed_at": str(session_row["completed_at"]) if session_row["completed_at"] else None,
        "questions": questions,
    }


def record_answer(
    session,
    repository_id: str,
    session_id: str,
    question_id: str,
    answer: str,
    user_id: Optional[str] = None,
) -> dict[str, Any]:
    """Record a contributor's answer to one offboarding question, turning it
    into a real, retrievable `knowledge_items` row (via Phase 5's
    `save_knowledge_item`) exactly like a knowledge-gap answer — this is
    what makes offboarding knowledge reusable by Historian later, not just
    text sitting in `offboarding_questions.answer`.

    Marks the session `completed` (with `completed_at`) once every question
    in it has a non-pending status.

    Args:
        session: Active SQLAlchemy session (not committed here).
        repository_id: Already-authorized repository id.
        session_id: The offboarding session this question belongs to.
        question_id: The `offboarding_questions.id` being answered.
        answer: The contributor's answer text.
        user_id: The user recording the answer, if known.

    Returns:
        The updated question dict (same shape as in `build_report`).

    Raises:
        ValueError: if the question doesn't belong to a session for this
            repository.
    """
    question_row = session.execute(
        text(
            """
            SELECT oq.id, oq.question
            FROM offboarding_questions oq
            JOIN offboarding_sessions os ON os.id = oq.session_id
            WHERE oq.id = :question_id AND oq.session_id = :session_id
              AND os.repository_id = :repository_id
            """
        ),
        {"question_id": question_id, "session_id": session_id, "repository_id": repository_id},
    ).mappings().first()

    if question_row is None:
        raise ValueError(
            f"No offboarding question {question_id!r} found in session {session_id!r} "
            f"for repository {repository_id!r}"
        )

    save_knowledge_item(
        session,
        repository_id=repository_id,
        title=question_row["question"][:120],
        content=answer,
        source="offboarding",
        user_id=user_id,
    )

    session.execute(
        text(
            """
            UPDATE offboarding_questions
            SET answer = :answer, status = 'answered'
            WHERE id = :question_id
            """
        ),
        {"answer": answer, "question_id": question_id},
    )

    remaining = session.execute(
        text(
            """
            SELECT COUNT(*) AS remaining
            FROM offboarding_questions
            WHERE session_id = :session_id AND status = 'pending'
            """
        ),
        {"session_id": session_id},
    ).mappings().one()

    if remaining["remaining"] == 0:
        session.execute(
            text(
                """
                UPDATE offboarding_sessions
                SET status = 'completed', completed_at = now()
                WHERE id = :session_id
                """
            ),
            {"session_id": session_id},
        )

    session.flush()

    updated = session.execute(
        text("SELECT id, question, priority, answer, status FROM offboarding_questions WHERE id = :question_id"),
        {"question_id": question_id},
    ).mappings().one()
    return _row_to_question(updated)
