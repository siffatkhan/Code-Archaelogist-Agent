"""
knowledge_gap_agent.py — formalizes the guardrail + gap-routing decision
from Phase 6 as its own callable agent.

Owner: M3 (Static Code Intelligence & AI/Knowledge Layer)
Phase: 7 — The Agents

Given a question, decides one of exactly three outcomes:
  - "off_topic"  — refused, never answered (guardrail caught it)
  - "needs_gap"  — evidence was insufficient; a `knowledge_gaps` row was
                   created (via Phase 5's `gap_detector`, reached through
                   Phase 6's `gap_check_node`)
  - "answerable" — evidence is strong enough that Historian can generate a
                   real answer for this question

This deliberately reuses Phase 6's individual node functions
(`guardrail_node`, `retrieval_node`, `gap_check_node`) directly rather than
running the full compiled graph — this agent doesn't need to reach
`answer_generation`/`classification` at all, and calling the nodes as plain
functions is exactly what Phase 6 built them for ("individually-testable
node functions"). This also means the decision logic here can never drift
out of sync with what Historian's graph actually does, since both paths
call the same node functions rather than each re-implementing the check.

This also backs `GET /repositories/{repository_id}/knowledge-gaps`
indirectly: `list_gaps` here is a thin passthrough to Phase 5's
`list_knowledge_gaps`, so M1's route for that endpoint has a single agent-
layer entry point to call, consistent with how `historian.py` and
`guidance_agent.py` are the entry points for their endpoints.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from ..graph.nodes import REFUSAL_MESSAGE, gap_check_node, guardrail_node, retrieval_node
from ..graph.state import GraphState
from ..services.knowledge.gap_detector import list_knowledge_gaps

Outcome = Literal["answerable", "needs_gap", "off_topic"]


def classify_question(
    session,
    repository_id: str,
    question: str,
    user_id: Optional[str] = None,
    context: Optional[str] = None,
) -> dict[str, Any]:
    """Decide whether a question is answerable, needs a gap, or is off-topic.

    Args:
        session: Active SQLAlchemy session.
        repository_id: Already-authorized repository id.
        question: The question to classify.
        user_id: Asking user's id, if known (provenance only).
        context: Optional extra context to store if this becomes a gap.

    Returns:
        A dict with:
          - `outcome`: one of "answerable" / "needs_gap" / "off_topic"
          - `refusal_message`: the exact refusal string when outcome is
            "off_topic", else None
          - `refusal_reason`: machine-readable reason when off-topic, else None
          - `evidence`: retrieved evidence (empty for the off-topic outcome,
            since retrieval never runs in that case)
          - `gap_id`: the created `knowledge_gaps` id when outcome is
            "needs_gap", else None
    """
    state: GraphState = {
        "repository_id": repository_id,
        "user_id": user_id,
        "question": question,
        "context": context,
        "session": session,
    }

    state.update(guardrail_node(state))
    if state.get("is_off_topic"):
        return {
            "outcome": "off_topic",
            "refusal_message": REFUSAL_MESSAGE,
            "refusal_reason": state.get("refusal_reason"),
            "evidence": [],
            "gap_id": None,
        }

    state.update(retrieval_node(state))
    state.update(gap_check_node(state))

    if state.get("gap_detected"):
        return {
            "outcome": "needs_gap",
            "refusal_message": None,
            "refusal_reason": None,
            "evidence": state.get("evidence", []),
            "gap_id": state.get("gap_id"),
        }

    return {
        "outcome": "answerable",
        "refusal_message": None,
        "refusal_reason": None,
        "evidence": state.get("evidence", []),
        "gap_id": None,
    }


def list_gaps(
    session,
    repository_id: str,
    status: Optional[str] = None,
) -> list[dict]:
    """Thin passthrough to Phase 5's `list_knowledge_gaps`, exposed here so
    `GET /repositories/{repository_id}/knowledge-gaps` has a single
    agent-layer function to call, consistent with the other two endpoints.
    """
    return list_knowledge_gaps(session, repository_id, status=status)
