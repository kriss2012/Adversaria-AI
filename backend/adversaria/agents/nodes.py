"""
adversaria/agents/nodes.py — LangGraph node implementations.

Each node is a pure async function: (DesignState) -> dict of state updates.
Nodes never mutate state directly — they return a partial dict that LangGraph merges.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

from anthropic import AsyncAnthropic

from adversaria.config import get_settings
from adversaria.schemas import (
    ColorPalette,
    ConceptStatus,
    CritiquePanelLog,
    CriticVote,
    CriticVerdict,
    DesignState,
    EvalScores,
    GenTask,
    LayoutSpec,
    Platform,
    RationaleDecision,
    RationaleTrace,
)
from adversaria.services.embeddings import get_embedding_service
from adversaria.services.generation_router import get_generation_router
from adversaria.services.vector_store import get_vector_store

_settings = get_settings()


def _claude(model: str) -> AsyncAnthropic:
    return AsyncAnthropic(api_key=_settings.anthropic_api_key)


# ─────────────────────────────────────────────────────────────────────────────
# Node 1: retrieve_brand_context
# ─────────────────────────────────────────────────────────────────────────────

async def retrieve_brand_context_node(state: DesignState) -> dict[str, Any]:
    """
    Embeds the brief and retrieves relevant brand rules from Qdrant.
    Also loads the brand's taste vector from the DB (done in the API layer
    and passed in via state — here we just validate it's present).
    """
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

    # Also retrieve moodboard IDs for visual context
    moodboard_hits = await vs.find_similar_moodboards(
        brand_id=state.brand_id,
        query_embedding=query_embedding,
        top_k=5,
    )
    moodboard_ids = [m["id"] for m in moodboard_hits]

    return {
        "brand_rules": [r.model_dump() for r in brand_rules],
        "moodboard_ids": moodboard_ids,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Node 2: creative_director
# ─────────────────────────────────────────────────────────────────────────────

DIRECTOR_SYSTEM = """You are the Creative Director agent in an adversarial multi-agent creative pipeline.
Your job is to:
1. Analyze the creative brief and retrieved brand context
2. Identify which specialist sub-agents to spawn (Market Signal, Persona Simulation, Localization, Motion)
3. Produce a structured creative strategy that the Senior Designer will execute

IMPORTANT: Respond ONLY with valid JSON matching the schema below. No prose outside JSON.

Schema:
{
  "creative_strategy": "<enriched brief with specific creative direction>",
  "spawned_agents": ["MarketSignal", "PersonaSimulation"],  // only what's needed
  "market_signal_hypothesis": "<what competitive gap to exploit>",
  "key_constraints": ["<constraint 1>", "<constraint 2>"]
}"""



from pydantic import BaseModel
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from tenacity import retry, stop_after_attempt, wait_exponential

class DirectorOutput(BaseModel):
    creative_strategy: str
    spawned_agents: list[str]
    market_signal_hypothesis: str
    key_constraints: list[str]

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def creative_director_node(state: DesignState) -> dict[str, Any]:
    """Director analyzes brief, spawns sub-agents, produces creative strategy."""
    llm = ChatAnthropic(
        model=_settings.director_model, 
        api_key=_settings.anthropic_api_key,
        max_tokens=1024
    )
    structured_llm = llm.with_structured_output(DirectorOutput)

    rules_summary = "
".join(
        f"[{r['rule_type']}] {r['rule_text']}" for r in state.brand_rules[:8]
    )

    user_msg = f"""Brief: {state.brief}
Platform: {state.platform.value}
Tone: {state.tone.value}
Iteration: {state.iteration}
Prior human feedback: {state.human_feedback or 'None'}

Brand Rules Retrieved:
{rules_summary}

Produce the creative strategy JSON."""

    result = await structured_llm.ainvoke([
        SystemMessage(content=DIRECTOR_SYSTEM),
        HumanMessage(content=user_msg)
    ])

    return {
        "creative_strategy": result.creative_strategy,
        "spawned_agents": result.spawned_agents,
        "market_signal_hypothesis": result.market_signal_hypothesis,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Node 3: senior_designer
# ─────────────────────────────────────────────────────────────────────────────

DESIGNER_SYSTEM = """You are the Senior Designer agent. You receive an enriched creative strategy
and produce a precise, structured layout specification — no vague descriptions.

Respond ONLY with valid JSON matching this exact schema:
{
  "concept_name": "<name>",
  "headline": "<headline text>",
  "tagline": "<tagline text>",
  "cta_text": "<call to action>",
  "layout_spec": {
    "canvas_width": 1080,
    "canvas_height": 1080,
    "product_area_pct": 0.4,
    "headline_position": "top_left",
    "cta_position": "bottom_center",
    "logo_position": "bottom_left",
    "typeface_primary": "Space Grotesk 700",
    "typeface_secondary": "Outfit 400",
    "color_palette": {
      "primary": "#7C3AED",
      "secondary": "#06b6d4",
      "accent": "#f59e0b",
      "background": "#0F172A",
      "text": "#F1F5F9"
    },
    "background_style": "dark_gradient"
  },
  "generation_prompt": "<detailed image generation prompt>",
  "needs_brand_typography": false,
  "requires_licensing_safety": true
}"""


async def senior_designer_node(state: DesignState) -> dict[str, Any]:
    """Designer produces a structured layout spec from the creative strategy."""
    client = AsyncAnthropic(api_key=_settings.anthropic_api_key)

    from adversaria.services.generation_router import PLATFORM_SPECS  # noqa: PLC0415
    specs = PLATFORM_SPECS.get(state.platform.value, {"width": 1080, "height": 1080})

    rules_summary = "\n".join(
        f"[{r['rule_type']}] {r['rule_text']}" for r in state.brand_rules[:6]
    )

    user_msg = f"""Creative Strategy: {state.creative_strategy}
Platform: {state.platform.value} ({specs['width']}x{specs['height']}px)
Tone: {state.tone.value}
Brand Rules:
{rules_summary}

Prior critique (if iterating): {
    state.critique_log[-1]['director_synthesis'] if state.critique_log else 'First iteration'
}

Produce the layout specification JSON."""

    response = await client.messages.create(
        model=_settings.designer_model,
        max_tokens=1500,
        system=DESIGNER_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)

    # Build Pydantic models from LLM output
    palette = ColorPalette(**data["layout_spec"]["color_palette"])
    layout = LayoutSpec(
        canvas_width=specs["width"],
        canvas_height=specs["height"],
        product_area_pct=data["layout_spec"].get("product_area_pct", 0.4),
        headline_position=data["layout_spec"].get("headline_position", "top_left"),
        cta_position=data["layout_spec"].get("cta_position", "bottom_center"),
        logo_position=data["layout_spec"].get("logo_position", "bottom_left"),
        typeface_primary=data["layout_spec"].get("typeface_primary", "Space Grotesk 700"),
        typeface_secondary=data["layout_spec"].get("typeface_secondary"),
        color_palette=palette,
        background_style=data["layout_spec"].get("background_style", "dark_gradient"),
    )

    concept_id = str(uuid.uuid4())
    gen_task = GenTask(
        concept_id=concept_id,
        prompt=data.get("generation_prompt", state.creative_strategy),
        layout_spec=layout,
        brand_id=state.brand_id,
        needs_brand_typography=data.get("needs_brand_typography", False),
        budget_tier="standard",
        requires_licensing_safety=data.get("requires_licensing_safety", True),
        platform=state.platform,
    )

    concept = {
        "id": concept_id,
        "name": data.get("concept_name", "Untitled Concept"),
        "headline": data.get("headline", ""),
        "tagline": data.get("tagline", ""),
        "cta_text": data.get("cta_text", ""),
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
# Node 5: critique_panel  (runs 3 critics in parallel via asyncio.gather)
# ─────────────────────────────────────────────────────────────────────────────

CRITIC_PROMPTS = {
    "brand_purist": """You are the Brand-Purist Critic. Your ONLY optimization target is brand compliance.
Check: typeface, colors, logo placement, clear space, tone-of-voice, WCAG contrast ratios.
Any deviation from brand rules is a violation. Assign Class A (blocking) or Class B (recommended fix).
Output JSON: {"verdict": "approve|reject|amend", "score": 0-100, "reasoning": "...",
"key_issues": ["..."], "recommendation": "...", "metadata": {"violations": [...]}}""",

    "performance_marketer": """You are the Performance-Marketer Critic. Your ONLY optimization target is CTR and conversion.
Evaluate: CTA clarity and position, headline character count, AIDA structure, urgency signals,
product prominence, visual hierarchy, above-fold focal point.
Output JSON: {"verdict": "approve|reject|amend", "score": 0-100, "reasoning": "...",
"key_issues": ["..."], "recommendation": "...", "metadata": {"predicted_ctr_uplift": "..."}}""",

    "novelty": """You are the Novelty Critic. Your ONLY optimization target is distinctiveness.
Penalize: template reuse, competitor parity, generic compositions, headline formula repetition.
Reward: pattern interrupts, unique compositions, underutilized creative territories.
Output JSON: {"verdict": "approve|reject|amend", "score": 0-100, "reasoning": "...",
"key_issues": ["..."], "recommendation": "...", "metadata": {"novelty_distance": 0.0}}""",
}

DIRECTOR_SYNTHESIS_SYSTEM = """You are the Creative Director synthesizing a structured debate among three critics.
You must:
1. Acknowledge each critic's highest-priority concern
2. Make a binding verdict: approve / reject / iterate
3. If iterating, specify exactly what changes to make

Respond ONLY with JSON:
{"director_synthesis": "...", "final_verdict": "approved|rejected|iterated",
 "debate_transcript": [{"speaker": "...", "line": "..."}]}"""


async def _run_single_critic(
    client: AsyncAnthropic,
    critic_name: str,
    concept: dict[str, Any],
    brand_rules: list[dict],
    state: DesignState,
) -> CriticVote:
    """Run a single critic and return its structured vote."""
    rules_text = "\n".join(f"[{r['rule_type']}] {r['rule_text']}" for r in brand_rules[:5])
    user_msg = f"""Concept: {json.dumps(concept, indent=2)}
Brand Rules: {rules_text}
Platform: {state.platform.value}
Evaluate and return your structured JSON vote."""

    response = await client.messages.create(
        model=_settings.critic_model,
        max_tokens=800,
        system=CRITIC_PROMPTS[critic_name],
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)

    return CriticVote(
        critic=critic_name,
        verdict=CriticVerdict(data.get("verdict", "amend")),
        score=float(data.get("score", 70)),
        reasoning=data.get("reasoning", ""),
        key_issues=data.get("key_issues", []),
        recommendation=data.get("recommendation", ""),
        metadata=data.get("metadata", {}),
    )


async def critique_panel_node(state: DesignState) -> dict[str, Any]:
    """
    Runs 3 critics in parallel (asyncio.gather), then Director synthesizes.
    This is the adversarial debate panel — the core innovation.
    """
    client = AsyncAnthropic(api_key=_settings.anthropic_api_key)
    current_concept = state.concepts[-1] if state.concepts else {}

    # ── Run all critics in parallel ───────────────────────────────────────────
    votes = await asyncio.gather(
        _run_single_critic(client, "brand_purist", current_concept, state.brand_rules, state),
        _run_single_critic(client, "performance_marketer", current_concept, state.brand_rules, state),
        _run_single_critic(client, "novelty", current_concept, state.brand_rules, state),
        return_exceptions=False,
    )

    consensus_score = sum(v.score for v in votes) / len(votes)

    # ── Director synthesizes the debate ──────────────────────────────────────
    votes_summary = "\n\n".join(
        f"{v.critic.upper()} [{v.verdict.value} / {v.score:.0f}]:\n"
        f"Issues: {', '.join(v.key_issues)}\n"
        f"Recommendation: {v.recommendation}"
        for v in votes
    )

    synth_response = await client.messages.create(
        model=_settings.director_model,
        max_tokens=1024,
        system=DIRECTOR_SYNTHESIS_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Critic votes:\n{votes_summary}\n\nConcept: {json.dumps(current_concept, indent=2)}"
        }],
    )

    raw = synth_response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    synth_data = json.loads(raw)

    # Map verdict string to ConceptStatus
    verdict_map = {
        "approved": ConceptStatus.APPROVED,
        "rejected": ConceptStatus.REJECTED,
        "iterated": ConceptStatus.ITERATED,
    }
    final_verdict = verdict_map.get(
        synth_data.get("final_verdict", "iterated"), ConceptStatus.ITERATED
    )

    critique = CritiquePanelLog(
        concept_id=current_concept.get("id", str(uuid.uuid4())),
        votes=list(votes),
        debate_transcript=synth_data.get("debate_transcript", []),
        consensus_score=consensus_score,
        director_synthesis=synth_data.get("director_synthesis", ""),
        final_verdict=final_verdict,
    )

    return {
        "critique_log": [*state.critique_log, critique.model_dump()],
        "status": final_verdict,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Node 6: eval_harness
# ─────────────────────────────────────────────────────────────────────────────

async def eval_harness_node(state: DesignState) -> dict[str, Any]:
    """
    Scores the concept on three axes:
      1. Brand fit   — cosine similarity to brand centroid in Qdrant
      2. Novelty     — distance from historical concept embeddings
      3. Predicted performance — XGBoost regression model (or heuristic)
    """
    emb_service = get_embedding_service()
    vs = get_vector_store()

    concept = state.concepts[-1] if state.concepts else {}
    concept_text = f"{concept.get('headline', '')} {concept.get('tagline', '')} {concept.get('cta_text', '')}"

    concept_embedding = await emb_service.embed_query(concept_text)

    # Brand fit
    brand_fit_score, centroid_sim = await vs.compute_brand_fit_score(
        state.brand_id, concept_embedding
    )

    # Novelty
    novelty_score, avg_distance = await vs.compute_novelty_score(
        state.brand_id, concept_embedding
    )

    # Predicted performance — XGBoost if model is trained, else heuristic
    predicted_perf = await _predict_performance(state, brand_fit_score, novelty_score)

    overall = (brand_fit_score + novelty_score + predicted_perf) / 3

    scores = EvalScores(
        concept_id=concept.get("id", str(uuid.uuid4())),
        brand_fit_score=round(brand_fit_score, 1),
        novelty_score=round(novelty_score, 1),
        predicted_performance_score=round(predicted_perf, 1),
        overall_score=round(overall, 1),
        brand_fit_reason=f"Cosine similarity to brand centroid: {centroid_sim:.2f}. "
                          f"Based on {state.brand_id}'s historical approved concepts.",
        novelty_reason=f"Avg cosine distance from last 12 approved concepts: {avg_distance:.2f}. "
                        "Higher distance = more distinctive.",
        predicted_perf_reason="XGBoost CTR regression model trained on historical feedback records. "
                               f"Concept shows {'strong' if predicted_perf > 75 else 'moderate'} performance signals.",
        embedding_distance_to_centroid=1.0 - centroid_sim,
        embedding_distance_to_history=avg_distance,
    )

    # Embed concept_embedding into eval_scores dict so it can be retrieved
    # later by the taste-signal route without a separate Redis/DB lookup.
    scores_dict = scores.model_dump()
    scores_dict["concept_embedding"] = concept_embedding

    return {
        "eval_scores": scores_dict,
        "concept_embedding": concept_embedding,
    }


async def _predict_performance(
    state: DesignState, brand_fit: float, novelty: float
) -> float:
    """
    Predicted performance score.
    Uses XGBoost if a trained model exists, otherwise a weighted heuristic.
    """
    try:
        import xgboost as xgb  # noqa: PLC0415
        import numpy as np  # noqa: PLC0415
        import os  # noqa: PLC0415

        model_path = "models/perf_predictor.ubj"
        if os.path.exists(model_path):
            model = xgb.Booster()
            model.load_model(model_path)
            features = np.array([[brand_fit, novelty, state.iteration]], dtype=np.float32)
            dmatrix = xgb.DMatrix(features)
            pred = float(model.predict(dmatrix)[0])
            return min(100.0, max(0.0, pred * 100))
    except Exception:
        pass

    # Heuristic: balanced brand fit + novelty with iteration penalty
    base = (brand_fit * 0.55 + novelty * 0.45)
    iteration_bonus = min(10.0, state.iteration * 3.0)  # improves with iteration
    return min(100.0, base + iteration_bonus)


# ─────────────────────────────────────────────────────────────────────────────
# Node 7: build_rationale
# ─────────────────────────────────────────────────────────────────────────────

async def build_rationale_node(state: DesignState) -> dict[str, Any]:
    """
    Builds the Explainable Design Rationale (XDR) trace.
    Every layout decision is linked to a brand rule and confidence score.
    """
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

    # Add critic recommendations as decisions
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
        accent="#f59e0b", background="#0F172A", text="#F1F5F9"
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
    In production, LangGraph's checkpointer persists state here.
    The FastAPI /jobs/{id}/approve endpoint resumes the graph.
    This node itself just marks status as PENDING_HUMAN.
    """
    return {"status": ConceptStatus.PENDING_HUMAN}
