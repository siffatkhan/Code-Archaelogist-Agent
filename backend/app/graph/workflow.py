"""
workflow.py — wires `nodes.py` into an actual LangGraph graph with
conditional branching.

Owner: M3 (Static Code Intelligence & AI/Knowledge Layer)
Phase: 6 — LangGraph Workflow

Graph shape
-----------
                    ┌──────────┐
                    │ guardrail │
                    └────┬─────┘
                 off-topic│   on-topic
                    ┌─────▼─────┐   ┌───────────┐
                    │  refusal  │   │ retrieval │
                    └─────┬─────┘   └─────┬─────┘
                          │               │
                         END        ┌─────▼──────┐
                                    │  gap_check  │
                                    └─────┬───────┘
                                 gap│           │no gap
                              ┌─────▼─────┐ ┌───▼────────────────┐
                              │gap_output │ │ answer_generation   │
                              └─────┬─────┘ └─────────┬───────────┘
                                    │                 │
                                   END          ┌──────▼───────┐
                                                │classification │
                                                └──────┬────────┘
                                                       │
                                                ┌──────▼───────┐
                                                │  finalize    │
                                                └──────┬────────┘
                                                       │
                                                      END

This mirrors the two required forks directly as graph edges (not as
if/else inside one big node): guardrail decides refusal vs. proceed, and
gap_check decides gap-creation vs. proceed to an answer — exactly the two
forks called out in the phase spec, and the reason LangGraph is being used
here at all rather than a plain function chain.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from .nodes import (
    answer_generation_node,
    classification_node,
    finalize_node,
    gap_check_node,
    gap_output_node,
    guardrail_node,
    refusal_node,
    retrieval_node,
)
from .state import GraphState


def _route_after_guardrail(state: GraphState) -> str:
    return "refusal" if state.get("is_off_topic") else "retrieval"


def _route_after_gap_check(state: GraphState) -> str:
    return "gap_output" if state.get("gap_detected") else "answer_generation"


def build_graph():
    """Construct (but don't run) the compiled LangGraph graph.

    Returns a compiled graph with an `.invoke(state: dict) -> dict` method.
    Call `build_graph()` once (e.g. at app startup, in Phase 7's agents) and
    reuse the compiled graph across requests — it's stateless itself; all
    per-request data lives in the state dict passed to `.invoke`.
    """
    graph = StateGraph(GraphState)

    graph.add_node("guardrail", guardrail_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("gap_check", gap_check_node)
    graph.add_node("answer_generation", answer_generation_node)
    graph.add_node("classification", classification_node)
    graph.add_node("refusal", refusal_node)
    graph.add_node("gap_output", gap_output_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("guardrail")

    graph.add_conditional_edges(
        "guardrail",
        _route_after_guardrail,
        {"refusal": "refusal", "retrieval": "retrieval"},
    )
    graph.add_edge("retrieval", "gap_check")
    graph.add_conditional_edges(
        "gap_check",
        _route_after_gap_check,
        {"gap_output": "gap_output", "answer_generation": "answer_generation"},
    )
    graph.add_edge("answer_generation", "classification")
    graph.add_edge("classification", "finalize")

    graph.add_edge("refusal", END)
    graph.add_edge("gap_output", END)
    graph.add_edge("finalize", END)

    return graph.compile()


def run_workflow(
    session,
    repository_id: str,
    question: str,
    user_id: str | None = None,
    context: str | None = None,
) -> dict:
    """Convenience entry point: build the graph and run it once for a single
    question. Phase 7's agents will likely build the graph once (via
    `build_graph()`) and reuse it, but this is here for simple/one-off calls
    and for the fixture tests below.

    Returns the `final_output` dict produced by whichever terminal node the
    graph reached (`refusal_node`, `gap_output_node`, or `finalize_node`).
    """
    compiled = build_graph()
    initial_state: GraphState = {
        "repository_id": repository_id,
        "user_id": user_id,
        "question": question,
        "context": context,
        "session": session,
    }
    result_state = compiled.invoke(initial_state)
    return result_state["final_output"]
