"""
historian.py — powers `POST /repositories/{repository_id}/questions`.

Owner: M3 (Static Code Intelligence & AI/Knowledge Layer)
Phase: 7 — The Agents

A thin, product-facing wrapper around Phase 6's compiled LangGraph workflow.
This module knows nothing about FastAPI, HTTP, or auth — it's a plain
Python function M1's route handler calls with an already-authorized
`repository_id` and a question, and gets back a dict shaped exactly like
the `/questions` response in the API Contract.

Response shape (API Contract, field names exact)
--------------------------------------------------
    { "answer": "string", "evidence": [], "confidence": "medium", "classification": "inferred" }
    classification values: verified, inferred, human_knowledge

Open question worth confirming with M1 before wiring the Pydantic response
model
--------------------------------------------------------------------------
The API Contract shows `confidence`/`classification` as plain strings, not
marked optional/nullable. But Phase 6's graph has two branches where no
answer is actually generated — off-topic refusal, and insufficient-evidence
(a gap was created instead of forcing an answer) — and for those there is
no honest `verified`/`inferred`/`human_knowledge` label to put on
"no answer was produced." Rather than invent a fourth fake classification
value (explicitly disallowed by this phase's rules) or silently pick one of
the three that would be misleading, this module returns `confidence: None`
/ `classification: None` for those two branches and always returns a
non-null, human-readable `answer` string either way. If the Pydantic
response model needs these fields non-nullable, that's a decision for M1 —
flagging it here rather than silently picking an answer.

For callers that want to distinguish these branches explicitly rather than
inferring it from null fields, this module also includes three additional
keys beyond the four in the API Contract: `is_refusal`, `gap_detected`, and
`gap_id`. These don't conflict with the required field names — they're
present alongside them — and M1's route/response model is free to drop them
if the API Contract's response should be exactly these four keys and no
others.
"""

from __future__ import annotations

from typing import Any, Optional

from ..graph.nodes import REFUSAL_MESSAGE
from ..graph.state import GraphState
from ..graph.workflow import build_graph

_GAP_ANSWER_MESSAGE = (
    "I don't have enough evidence in this repository to answer that confidently. "
    "This question has been logged as a knowledge gap for a maintainer to answer."
)

_compiled_graph = None


def _get_graph():
    """Build the graph once and reuse it across calls (it's stateless; all
    per-request data lives in the state dict passed to `.invoke`).
    """
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def answer_question(
    session,
    repository_id: str,
    question: str,
    user_id: Optional[str] = None,
    context: Optional[str] = None,
) -> dict[str, Any]:
    """Answer a question about a repository via Phase 6's full graph.

    Args:
        session: Active SQLAlchemy session (Phase 4/5's functions all take
            one; this just threads it through to the graph).
        repository_id: Already-authorized repository id.
        question: The user's question, e.g.
            "Why does this authentication middleware exist?"
        user_id: The asking user's id, if known (for provenance only; not
            used for authorization here).
        context: Optional extra context to attach if this question turns
            into a knowledge gap.

    Returns:
        A dict with `answer`, `evidence`, `confidence`, `classification`
        (the exact `/questions` response fields), plus `is_refusal`,
        `gap_detected`, `gap_id` — see module docstring.
    """
    graph = _get_graph()
    initial_state: GraphState = {
        "repository_id": repository_id,
        "user_id": user_id,
        "question": question,
        "context": context,
        "session": session,
    }
    result_state = graph.invoke(initial_state)
    final = result_state["final_output"]

    if final.get("gap_detected"):
        answer = _GAP_ANSWER_MESSAGE
    elif final.get("is_refusal"):
        answer = final.get("answer") or REFUSAL_MESSAGE
    else:
        answer = final.get("answer")

    return {
        "answer": answer,
        "evidence": final.get("evidence", []),
        "confidence": final.get("confidence"),
        "classification": final.get("classification"),
        "is_refusal": bool(final.get("is_refusal", False)),
        "gap_detected": bool(final.get("gap_detected", False)),
        "gap_id": final.get("gap_id"),
    }
