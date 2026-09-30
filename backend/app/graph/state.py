"""
state.py — the shared state object that flows through the LangGraph pipeline.

Owner: M3 (Static Code Intelligence & AI/Knowledge Layer)
Phase: 6 — LangGraph Workflow

This is a plain `TypedDict` (LangGraph's standard state shape) rather than a
Pydantic model, so nodes can return small partial dicts and let LangGraph
merge them into the running state, instead of every node having to
reconstruct a full model instance.

`total=False` because most fields don't exist yet when the graph starts (or
never get populated on some branches — e.g. `answer` stays unset on the
off-topic and gap-detected branches) — that's expected, not an error.

Field lifecycle by branch
--------------------------
Every branch populates: question/repository_id/session (input), is_off_topic,
final_output.
  - Off-topic branch stops there: guardrail -> refusal -> final_output.
  - Gap branch adds: evidence, best_similarity, gap_detected, gap_id, then
    final_output.
  - Normal answer branch adds all of the above plus: answer, classification,
    confidence, then final_output.

`session` note
--------------
`session` carries a live SQLAlchemy `Session` (from Phase 4/5's functions,
which all take one) through the graph so nodes can call retrieval/knowledge
functions. It is not JSON-serializable and is not meant to be persisted or
checkpointed — if this graph is ever run with LangGraph's persistence/
checkpointing enabled, `session` must be excluded from whatever gets
serialized (e.g. re-injected at invoke time rather than stored), same as any
other live DB handle or connection.
"""

from __future__ import annotations

from typing import Any, Literal, Optional, TypedDict

Classification = Literal["verified", "inferred", "human_knowledge"]
Confidence = Literal["high", "medium", "low"]


class EvidenceItem(TypedDict):
    """One retrieved item, shaped like `vector_search.SearchResult` (Phase 4)."""

    id: str
    knowledge_item_id: Optional[str]
    content: str
    similarity: float


class FinalOutput(TypedDict, total=False):
    """What the graph produces on every branch. Phase 7's agents adapt this
    into the exact API Contract response shapes for each endpoint — this
    graph's job is just to produce a complete, unambiguous result.
    """

    answer: Optional[str]
    evidence: list[EvidenceItem]
    classification: Optional[Classification]
    confidence: Optional[Confidence]
    is_refusal: bool
    refusal_reason: Optional[str]
    gap_detected: bool
    gap_id: Optional[str]


class GraphState(TypedDict, total=False):
    # --- input (set by the caller before invoking the graph) ---
    repository_id: str
    user_id: Optional[str]
    question: str
    context: Optional[str]
    session: Any  # SQLAlchemy Session; see module docstring

    # --- guardrail node output ---
    is_off_topic: bool
    refusal_reason: Optional[str]

    # --- retrieval node output ---
    evidence: list[EvidenceItem]
    best_similarity: Optional[float]

    # --- gap-check node output ---
    gap_detected: bool
    gap_id: Optional[str]

    # --- answer-generation node output ---
    answer: Optional[str]

    # --- classification node output ---
    classification: Optional[Classification]
    confidence: Optional[Confidence]

    # --- terminal output (set by refusal_node / gap_output_node / finalize_node) ---
    final_output: FinalOutput
