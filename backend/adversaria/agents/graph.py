"""
adversaria/agents/graph.py — LangGraph StateGraph definition.

Architecture:
  retrieve_brand_context → creative_director → senior_designer
    → generate_image → critique_panel
    → [conditional] human_review OR senior_designer (iterate)
    → eval_harness → build_rationale → END

The conditional edge on critique confidence is the key structural choice —
HITL is adaptive, not a blanket checkpoint every time.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from adversaria.schemas import ConceptStatus, DesignState
from adversaria.agents.nodes import (
    retrieve_brand_context_node,
    creative_director_node,
    senior_designer_node,
    generate_image_node,
    critique_panel_node,
    eval_harness_node,
    build_rationale_node,
    human_review_node,
)

# ─── Routing functions ────────────────────────────────────────────────────────

def route_after_critique(state: DesignState) -> str:
    """
    Conditional edge: after critique panel decides the path forward.
    - APPROVED → go straight to eval (high-confidence, skip HITL)
    - REJECTED → back to director (start over with feedback)
    - ITERATED → back to designer (fix specific issues, keep strategy)
    - PENDING_HUMAN → human review gate (medium confidence)
    - Max iterations reached → force to human review regardless
    """
    if state.iteration >= state.max_iterations:
        return "human_review"

    last_critique = state.critique_log[-1] if state.critique_log else None
    if not last_critique:
        return "senior_designer"

    verdict = last_critique.get("final_verdict", ConceptStatus.ITERATED.value)
    confidence = last_critique.get("consensus_score", 0)

    # High confidence approval → skip HITL, go to eval
    if verdict == ConceptStatus.APPROVED.value and confidence >= 80:
        return "eval_harness"

    # Low confidence or pending → require human review
    if confidence < 60 or verdict == ConceptStatus.REJECTED.value:
        return "human_review"

    # Designer-level iteration (specific fixes)
    if verdict == ConceptStatus.ITERATED.value:
        return "senior_designer"

    return "human_review"


def route_after_human_review(state: DesignState) -> str:
    """
    After human reviews:
    - Approved → proceed to eval
    - Rejected → back to Director (full restart with new strategy)
    """
    if state.human_approved:
        return "eval_harness"
    return "creative_director"


# ─── Graph builder ────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Constructs and compiles the LangGraph StateGraph.
    Uses Pydantic DesignState as the typed state schema.
    """
    graph = StateGraph(DesignState)

    # ── Register nodes ────────────────────────────────────────────────────────
    graph.add_node("retrieve_brand_context", retrieve_brand_context_node)
    graph.add_node("creative_director", creative_director_node)
    graph.add_node("senior_designer", senior_designer_node)
    graph.add_node("generate_image", generate_image_node)
    graph.add_node("critique_panel", critique_panel_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("eval_harness", eval_harness_node)
    graph.add_node("build_rationale", build_rationale_node)

    # ── Entry point ───────────────────────────────────────────────────────────
    graph.set_entry_point("retrieve_brand_context")

    # ── Static edges (linear path) ────────────────────────────────────────────
    graph.add_edge("retrieve_brand_context", "creative_director")
    graph.add_edge("creative_director", "senior_designer")
    graph.add_edge("senior_designer", "generate_image")
    graph.add_edge("generate_image", "critique_panel")

    # ── Conditional edges (the adaptive HITL routing) ─────────────────────────
    graph.add_conditional_edges(
        "critique_panel",
        route_after_critique,
        {
            "senior_designer": "senior_designer",
            "human_review": "human_review",
            "eval_harness": "eval_harness",
            "creative_director": "creative_director",
        },
    )
    graph.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "eval_harness": "eval_harness",
            "creative_director": "creative_director",
        },
    )

    # ── Terminal path ─────────────────────────────────────────────────────────
    graph.add_edge("eval_harness", "build_rationale")
    graph.add_edge("build_rationale", END)

    return graph


async def create_compiled_graph(checkpointer: AsyncPostgresSaver | None = None):
    """
    Returns a compiled LangGraph app with optional Postgres checkpointing.
    The checkpointer enables resumable HITL — a human can approve hours later.
    """
    graph = build_graph()
    if checkpointer:
        return graph.compile(checkpointer=checkpointer, interrupt_before=["human_review"])
    return graph.compile()
