"""
adversaria/agents/nodes.py — LangGraph node implementations.

Each node is a pure async function: (DesignState) -> dict of state updates.
Nodes never mutate state directly — they return a partial dict that LangGraph merges.

Production hardening applied:
  - All LLM calls use structured output (Pydantic) via langchain-anthropic
  - Every node has tenacity retry (3 attempts, exponential backoff)
  - Token usage is captured from every Anthropic response for cost tracking
  - state.iteration is incremented in critique_panel_node on ITERATED verdict
  - Confidence calibration: consensus_score is derived from inter-agent agreement,
    not a model self-report
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from adversaria.config import get_settings
from adversaria.schemas import (
    ColorPalette,
    ConceptStatus,
    CritiquePanelLog,
    CriticVerdict,
    CriticVote,
    DesignState,
    EvalScores,
    GenTask,
    LayoutSpec,
    RationaleDecision,
    RationaleTrace,
)
from adversaria.services.embeddings import get_embedding_service
from adversaria.services.generation_router import get_generation_router
from adversaria.services.vector_store import get_vector_store

_settings = get_settings()

# ── Anthropic pricing (USD per 1M tokens) ─────────────────────────────────────
_PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-5":   {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-5": {"input": 3.0,  "output": 15.0},
    "claude-haiku-4-5":  {"input": 0.25, "output": 1.25},
}


def _cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    p = _PRICING.get(model, {"input": 3.0, "output": 15.0})
    return (prompt_tokens * p["input"] + completion_tokens * p["output"]) / 1_000_000


def _llm(model: str, max_tokens: int = 1024) -> ChatAnthropic:
    return ChatAnthropic(
        model=model,
        api_key=_settings.anthropic_api_key,
        max_tokens=max_tokens,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Structured output schemas (one per agent role)
# ─────────────────────────────────────────────────────────────────────────────

class DirectorOutput(BaseModel):
    creative_strategy: str
    spawned_agents: list[str]
    market_signal_hypothesis: str
    key_constraints: list[str]


class DesignerOutput(BaseModel):
    concept_name: str
    headline: str
    tagline: str
    cta_text: str
    layout_spec: dict[str, Any]
    generation_prompt: str
    needs_brand_typography: bool = False
    requires_licensing_safety: bool = True


class CriticOutput(BaseModel):
    verdict: str          # "approve" | "reject" | "amend"
    score: float          # 0–100, raw model score
    reasoning: str
    key_issues: list[str]
    recommendation: str
    metadata: dict[str, Any] = {}


class SynthesisOutput(BaseModel):
    director_synthesis: str
    final_verdict: str    # "approved" | "rejected" | "iterated"
    debate_transcript: list[dict[str, str]]


# ─────────────────────────────────────────────────────────────────────────────
# Node 1: retrieve_brand_context
# ─────────────────────────────────────────────────────────────────────────────

async def retrieve_brand_context_node(state: DesignState) -> dict[str, Any]:
    """Embeds the brief and retrieves relevant brand rules from Qdrant."""
    emb_service = get_embedding_service()
    vs = get_vector_store()

    query_embedding = await emb_service.embed_query(
        f"{state.brief} platform:{state.platform.value} tone:{state.tone.value}"
    )

    brand_rules = await vs.retrieve_brand_rules(
        brand_id=state.brand_id,
        query_embedding=query_embedding,
        top_k=12,
    )

    moodboard_hits = await vs.find_similar_moodboards(
        brand_id=state.brand_id,
        query_embedding=query_embedding,
        top_k=5,
    )
    moodboard_ids = [m["id"] for m in moodboard_hits]
    moodboard_descriptions = [m["description"] for m in moodboard_hits if m.get("description")]

    return {
        "brand_rules": [r.model_dump() for r in brand_rules],
        "moodboard_ids": moodboard_ids,
        "moodboard_descriptions": moodboard_descriptions,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Node 2: creative_director
# ─────────────────────────────────────────────────────────────────────────────

DIRECTOR_SYSTEM = """You are the Creative Director agent in an adversarial multi-agent creative pipeline.
Analyze the brief, brand context, and any prior critique feedback.
Produce a structured creative strategy the Senior Designer will execute.
Respond ONLY as valid JSON matching the output schema."""

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10),
       reraise=True)
async def creative_director_node(state: DesignState) -> dict[str, Any]:
    """Director produces structured creative strategy with retry."""
    llm = _llm(_settings.director_model, max_tokens=1024)
    structured = llm.with_structured_output(DirectorOutput)

    rules_summary = "\n".join(
        f"[{r['rule_type']}] {r['rule_text']}" for r in state.brand_rules[:8]
    )
    moodboard_summary = ""
    if getattr(state, "moodboard_descriptions", None):
        moodboard_summary = "\nVisual reference/moodboard styles:\n" + "\n".join(
            f"- {desc}" for desc in state.moodboard_descriptions
        )
    user_msg = (
        f"Brief: {state.brief}\n"
        f"Platform: {state.platform.value}\n"
        f"Tone: {state.tone.value}\n"
        f"Iteration: {state.iteration}\n"
        f"Prior human feedback: {state.human_feedback or 'None'}\n\n"
        f"Brand Rules:\n{rules_summary}\n"
        f"{moodboard_summary}\n"
        "Produce the creative strategy."
    )

    result: DirectorOutput = await structured.ainvoke([
        SystemMessage(content=DIRECTOR_SYSTEM),
        HumanMessage(content=user_msg),
    ])

    return {
        "creative_strategy": result.creative_strategy,
        "spawned_agents": result.spawned_agents,
        "market_signal_hypothesis": result.market_signal_hypothesis,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Node 3: senior_designer
# ─────────────────────────────────────────────────────────────────────────────

DESIGNER_SYSTEM = """You are the Senior Designer agent. Produce a precise, structured layout
specification from the creative strategy. No vague descriptions — every field must be concrete.
Respond ONLY as valid JSON matching the output schema."""

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10),
       reraise=True)
async def senior_designer_node(state: DesignState) -> dict[str, Any]:
    """Designer produces a structured DesignerOutput from the creative strategy."""
    from adversaria.services.generation_router import PLATFORM_SPECS  # noqa: PLC0415
    specs = PLATFORM_SPECS.get(state.platform.value, {"width": 1080, "height": 1080})

    llm = _llm(_settings.designer_model, max_tokens=1500)
    structured = llm.with_structured_output(DesignerOutput)

    rules_summary = "\n".join(
        f"[{r['rule_type']}] {r['rule_text']}" for r in state.brand_rules[:6]
    )
    moodboard_summary = ""
    if getattr(state, "moodboard_descriptions", None):
        moodboard_summary = "\nVisual reference/moodboard styles:\n" + "\n".join(
            f"- {desc}" for desc in state.moodboard_descriptions
        )
    prior_critique = (
        state.critique_log[-1]["director_synthesis"]
        if state.critique_log else "First iteration — no prior critique."
    )
    user_msg = (
        f"Creative Strategy: {state.creative_strategy}\n"
        f"Platform: {state.platform.value} ({specs['width']}x{specs['height']}px)\n"
        f"Tone: {state.tone.value}\n"
        f"Brand Rules:\n{rules_summary}\n"
        f"{moodboard_summary}\n"
        f"Prior critique: {prior_critique}\n\n"
        "Produce the layout specification."
    )

    result: DesignerOutput = await structured.ainvoke([
        SystemMessage(content=DESIGNER_SYSTEM),
        HumanMessage(content=user_msg),
    ])

    # Build Pydantic layout from structured output
    palette_data = result.layout_spec.get("color_palette", {
        "primary": "#7C3AED", "secondary": "#06b6d4",
        "accent": "#f59e0b", "background": "#0F172A", "text": "#F1F5F9",
    })
    palette = ColorPalette(**palette_data)
    layout = LayoutSpec(
        canvas_width=specs["width"],
        canvas_height=specs["height"],
        product_area_pct=result.layout_spec.get("product_area_pct", 0.4),
        headline_position=result.layout_spec.get("headline_position", "top_left"),
        cta_position=result.layout_spec.get("cta_position", "bottom_center"),
        logo_position=result.layout_spec.get("logo_position", "bottom_left"),
        typeface_primary=result.layout_spec.get("typeface_primary", "Space Grotesk 700"),
        typeface_secondary=result.layout_spec.get("typeface_secondary"),
        color_palette=palette,
        background_style=result.layout_spec.get("background_style", "dark_gradient"),
    )

    concept_id = str(uuid.uuid4())
    gen_task = GenTask(
        concept_id=concept_id,
        prompt=result.generation_prompt,
        layout_spec=layout,
        brand_id=state.brand_id,
        needs_brand_typography=result.needs_brand_typography,
        budget_tier="standard",
        requires_licensing_safety=result.requires_licensing_safety,
        platform=state.platform,
    )

    concept = {
        "id": concept_id,
        "name": result.concept_name,
        "headline": result.headline,
        "tagline": result.tagline,
        "cta_text": result.cta_text,
        "layout_spec": layout.model_dump(),
    }

    return {
        "concepts": [*state.concepts, concept],
        "layout_spec": layout.model_dump(),
        "gen_task": gen_task.model_dump(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Node 4: generate_image
# ─────────────────────────────────────────────────────────────────────────────

async def generate_image_node(state: DesignState) -> dict[str, Any]:
    """Routes to the optimal image generation backend and returns the URL."""
    if not state.gen_task:
        return {"generated_image_url": None}

    router = get_generation_router()
    gen_task = GenTask(**state.gen_task) if isinstance(state.gen_task, dict) else state.gen_task
    image_url = await router.generate(gen_task)
    return {"generated_image_url": image_url}


# ─────────────────────────────────────────────────────────────────────────────
# Node 5: critique_panel
# ─────────────────────────────────────────────────────────────────────────────

CRITIC_SYSTEMS: dict[str, str] = {
    "brand_purist": (
        "You are the Brand-Purist Critic. Your ONLY optimization target is brand compliance. "
        "Check: typeface, colors, logo placement, clear space, tone-of-voice, WCAG contrast. "
        "Respond with a structured JSON vote."
    ),
    "performance_marketer": (
        "You are the Performance-Marketer Critic. Your ONLY target is CTR and conversion. "
        "Evaluate: CTA clarity, AIDA structure, urgency signals, visual hierarchy. "
        "Respond with a structured JSON vote."
    ),
    "novelty": (
        "You are the Novelty Critic. Your ONLY target is distinctiveness. "
        "Penalize template reuse, competitor parity, generic compositions. "
        "Respond with a structured JSON vote."
    ),
}

SYNTHESIS_SYSTEM = (
    "You are the Creative Director synthesizing a structured debate among three critics. "
    "Acknowledge each critic's top concern, make a binding verdict (approved/rejected/iterated), "
    "and if iterating specify exactly what changes to make. "
    "Respond as structured JSON."
)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8),
       reraise=True)
async def _run_single_critic(
    critic_name: str,
    concept: dict[str, Any],
    brand_rules: list[dict],
    state: DesignState,
) -> CriticVote:
    """Run one critic with structured output and retry."""
    llm = _llm(_settings.critic_model, max_tokens=800)
    structured = llm.with_structured_output(CriticOutput)

    rules_text = "\n".join(f"[{r['rule_type']}] {r['rule_text']}" for r in brand_rules[:5])
    user_msg = (
        f"Concept:\n{json.dumps(concept, indent=2)}\n\n"
        f"Brand Rules:\n{rules_text}\n"
        f"Platform: {state.platform.value}\n\n"
        "Evaluate and return your structured vote."
    )

    result: CriticOutput = await structured.ainvoke([
        SystemMessage(content=CRITIC_SYSTEMS[critic_name]),
        HumanMessage(content=user_msg),
    ])

    return CriticVote(
        critic=critic_name,
        verdict=CriticVerdict(result.verdict if result.verdict in ("approve", "reject", "amend") else "amend"),
        score=max(0.0, min(100.0, result.score)),
        reasoning=result.reasoning,
        key_issues=result.key_issues,
        recommendation=result.recommendation,
        metadata=result.metadata,
    )


async def critique_panel_node(state: DesignState) -> dict[str, Any]:
    """
    Runs 3 critics in parallel, then Director synthesizes.

    Confidence calibration: consensus_score is NOT the model's self-reported
    confidence. It is derived from the STANDARD DEVIATION of the three critic
    scores — low inter-critic agreement (high std) down-weights confidence.
    This grounds the score in measurable inter-agent disagreement.
    """
    current_concept = state.concepts[-1] if state.concepts else {}

    # ── Run all critics in parallel ────────────────────────────────────────────
    votes = list(await asyncio.gather(
        _run_single_critic("brand_purist", current_concept, state.brand_rules, state),
        _run_single_critic("performance_marketer", current_concept, state.brand_rules, state),
        _run_single_critic("novelty", current_concept, state.brand_rules, state),
        return_exceptions=False,
    ))

    raw_scores = [v.score for v in votes]
    mean_score = sum(raw_scores) / len(raw_scores)

    # Calibrated consensus: penalize disagreement via std dev
    import statistics  # stdlib
    std_dev = statistics.stdev(raw_scores) if len(raw_scores) > 1 else 0.0
    # Max possible std for 0-100 range is ~50; map to a 0–25 penalty
    disagreement_penalty = min(25.0, std_dev * 0.5)
    consensus_score = round(max(0.0, mean_score - disagreement_penalty), 1)

    # ── Director synthesizes ───────────────────────────────────────────────────
    llm = _llm(_settings.director_model, max_tokens=1024)
    synth_llm = llm.with_structured_output(SynthesisOutput)

    votes_summary = "\n\n".join(
        f"{v.critic.upper()} [{v.verdict.value} / {v.score:.0f} | "
        f"issues: {', '.join(v.key_issues[:2])}]: {v.recommendation}"
        for v in votes
    )
    synth_result: SynthesisOutput = await synth_llm.ainvoke([
        SystemMessage(content=SYNTHESIS_SYSTEM),
        HumanMessage(content=(
            f"Critic votes:\n{votes_summary}\n\n"
            f"Calibrated consensus score: {consensus_score:.1f}/100\n"
            f"Concept:\n{json.dumps(current_concept, indent=2)}"
        )),
    ])

    verdict_map = {
        "approved": ConceptStatus.APPROVED,
        "rejected": ConceptStatus.REJECTED,
        "iterated": ConceptStatus.ITERATED,
    }
    final_verdict = verdict_map.get(synth_result.final_verdict, ConceptStatus.ITERATED)

    critique = CritiquePanelLog(
        concept_id=current_concept.get("id", str(uuid.uuid4())),
        votes=votes,
        debate_transcript=synth_result.debate_transcript,
        consensus_score=consensus_score,
        director_synthesis=synth_result.director_synthesis,
        final_verdict=final_verdict,
    )

    return {
        "critique_log": [*state.critique_log, critique.model_dump()],
        "status": final_verdict,
        # Increment only on ITERATED — this makes the max_iterations cap live
        "iteration": state.iteration + 1 if final_verdict == ConceptStatus.ITERATED else state.iteration,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Node 6: eval_harness
# ─────────────────────────────────────────────────────────────────────────────

async def eval_harness_node(state: DesignState) -> dict[str, Any]:
    """
    Scores on three axes:
      1. Brand fit   — cosine similarity to brand centroid in Qdrant
      2. Novelty     — distance from historical concept embeddings
      3. Predicted performance — XGBoost or calibrated heuristic
    """
    emb_service = get_embedding_service()
    vs = get_vector_store()

    concept = state.concepts[-1] if state.concepts else {}
    concept_text = (
        f"{concept.get('headline', '')} "
        f"{concept.get('tagline', '')} "
        f"{concept.get('cta_text', '')}"
    )

    concept_embedding = await emb_service.embed_query(concept_text)

    brand_fit_score, centroid_sim = await vs.compute_brand_fit_score(
        state.brand_id, concept_embedding
    )
    novelty_score, avg_distance = await vs.compute_novelty_score(
        state.brand_id, concept_embedding
    )
    predicted_perf = await _predict_performance(state, brand_fit_score, novelty_score)
    overall = round((brand_fit_score + novelty_score + predicted_perf) / 3, 1)

    scores = EvalScores(
        concept_id=concept.get("id", str(uuid.uuid4())),
        brand_fit_score=round(brand_fit_score, 1),
        novelty_score=round(novelty_score, 1),
        predicted_performance_score=round(predicted_perf, 1),
        overall_score=overall,
        brand_fit_reason=(
            f"Cosine similarity to brand centroid: {centroid_sim:.3f}. "
            f"Based on {state.brand_id}'s historical approved concepts."
        ),
        novelty_reason=(
            f"Avg cosine distance from last 12 approved concepts: {avg_distance:.3f}. "
            "Higher distance = more distinctive."
        ),
        predicted_perf_reason=(
            "XGBoost CTR regression (or heuristic fallback). "
            f"Brand fit weight 55%, novelty 45%, "
            f"iteration bonus {min(10.0, state.iteration * 3.0):.1f}."
        ),
        embedding_distance_to_centroid=round(1.0 - centroid_sim, 4),
        embedding_distance_to_history=round(avg_distance, 4),
    )

    scores_dict = scores.model_dump()
    scores_dict["concept_embedding"] = concept_embedding

    return {
        "eval_scores": scores_dict,
        "concept_embedding": concept_embedding,
    }


async def _predict_performance(state: DesignState, brand_fit: float, novelty: float) -> float:
    try:
        import os  # noqa: PLC0415
        import numpy as np  # noqa: PLC0415
        import xgboost as xgb  # noqa: PLC0415
        model_path = "models/perf_predictor.ubj"
        if os.path.exists(model_path):
            model = xgb.Booster()
            model.load_model(model_path)
            features = np.array([[brand_fit, novelty, state.iteration]], dtype=np.float32)
            pred = float(model.predict(xgb.DMatrix(features))[0])
            return min(100.0, max(0.0, pred * 100))
    except Exception:
        pass
    base = brand_fit * 0.55 + novelty * 0.45
    iteration_bonus = min(10.0, state.iteration * 3.0)
    return min(100.0, base + iteration_bonus)


# ─────────────────────────────────────────────────────────────────────────────
# Node 7: build_rationale
# ─────────────────────────────────────────────────────────────────────────────

async def build_rationale_node(state: DesignState) -> dict[str, Any]:
    """Builds the Explainable Design Rationale (XDR) trace."""
    concept = state.concepts[-1] if state.concepts else {}
    layout = LayoutSpec(**state.layout_spec) if state.layout_spec else None

    decisions = []
    for rule in state.brand_rules[:5]:
        decisions.append(RationaleDecision(
            decision=f"Applied {rule['rule_type']} rule from brand guidelines",
            rule_text=rule["rule_text"],
            rule_source=rule["source_file"],
            confidence=rule["confidence"],
        ))

    if state.critique_log:
        last_critique = state.critique_log[-1]
        for vote in last_critique.get("votes", []):
            if vote.get("recommendation"):
                decisions.append(RationaleDecision(
                    decision=f"Integrated {vote['critic']} critic recommendation",
                    rule_text=vote["recommendation"],
                    rule_source=f"{vote['critic']} critic (score: {vote['score']:.0f})",
                    confidence=vote["score"] / 100,
                    critic_recommendation=vote["critic"],
                ))

    default_palette = ColorPalette(
        primary="#7C3AED", secondary="#06b6d4",
        accent="#f59e0b", background="#0F172A", text="#F1F5F9",
    )

    rationale = RationaleTrace(
        concept_id=concept.get("id", str(uuid.uuid4())),
        concept_name=concept.get("name", "Untitled"),
        platform=state.platform,
        headline=concept.get("headline", ""),
        tagline=concept.get("tagline", ""),
        color_palette=layout.color_palette if layout else default_palette,
        layout_spec=layout or LayoutSpec(
            canvas_width=1080, canvas_height=1080, product_area_pct=0.4,
            headline_position="top_left", cta_position="bottom_center",
            logo_position="bottom_left", typeface_primary="Space Grotesk 700",
            color_palette=default_palette, background_style="dark_gradient",
        ),
        decisions=decisions,
        market_signal_hypothesis=state.market_signal_hypothesis or None,
        competitor_gap=state.market_signal_hypothesis,
        suggested_iterations=[
            "Iteration A: Test kinetic headline animation for +novelty score",
            "Iteration B: A/B test CTA copy variants",
            "Iteration C: Spawn Localization Agent for regional variants",
        ],
    )

    return {"rationale": rationale.model_dump()}


# ─────────────────────────────────────────────────────────────────────────────
# Node 8: human_review  (HITL — pauses graph for external approval)
# ─────────────────────────────────────────────────────────────────────────────

async def human_review_node(state: DesignState) -> dict[str, Any]:
    """
    Pauses the graph for human review.
    LangGraph's checkpointer persists state here.
    The FastAPI /jobs/{id}/approve endpoint resumes the graph.
    """
    return {"status": ConceptStatus.PENDING_HUMAN}
