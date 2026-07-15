"""
adversaria/schemas.py — Pydantic v2 schemas for all agent handoffs.

These are the canonical typed contracts between every node in the LangGraph.
Never pass free text between agents — always use these models.
"""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class Platform(str, Enum):
    INSTAGRAM_FEED = "instagram_feed_1x1"
    INSTAGRAM_STORY = "instagram_story_9x16"
    LINKEDIN_SINGLE = "linkedin_single_4x5"
    BANNER_16_9 = "banner_16x9"
    META_ADS = "meta_ads_1x1"
    TIKTOK = "tiktok_9x16"


class ToneProfile(str, Enum):
    ENERGETIC = "energetic_bold"
    MINIMALIST = "minimalist_clean"
    WARM = "warm_trustworthy"
    FUTURISTIC = "futuristic_tech"
    LUXURY = "luxury_premium"


class CriticVerdict(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    AMEND = "amend"


class ConceptStatus(str, Enum):
    DRAFT = "draft"
    CRITIQUED = "critiqued"
    ITERATED = "iterated"
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING_HUMAN = "pending_human"


class GenerationBackend(str, Enum):
    FLUX_PRO = "flux_pro"
    FLUX_SCHNELL = "flux_schnell"          # draft tier
    SDXL_TURBO = "sdxl_turbo"             # draft tier
    COMFYUI_LORA = "comfyui_custom_lora"  # brand-typography fine-tuned
    FIREFLY = "firefly"                    # licensing-safe
    DALLE3 = "dalle3"


# ─────────────────────────────────────────────────────────────────────────────
# Sub-schemas
# ─────────────────────────────────────────────────────────────────────────────

class BrandRule(BaseModel):
    """A single semantic unit retrieved from the brand corpus."""
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rule_type: str  # e.g. "typography", "color", "logo_placement", "tone"
    rule_text: str
    source_file: str
    confidence: float = Field(ge=0.0, le=1.0)
    embedding_distance: float = Field(ge=0.0, le=2.0)  # distance from query


class ColorPalette(BaseModel):
    primary: str       # hex
    secondary: str     # hex
    accent: str        # hex
    background: str    # hex
    text: str          # hex


class LayoutSpec(BaseModel):
    """Structured layout definition — no free text."""
    canvas_width: int
    canvas_height: int
    product_area_pct: float = Field(ge=0.0, le=1.0)
    headline_position: str   # e.g. "top_left", "center"
    cta_position: str
    logo_position: str
    typeface_primary: str
    typeface_secondary: str | None = None
    color_palette: ColorPalette
    background_style: str    # e.g. "dark_gradient", "flat_white", "texture"


class CriticVote(BaseModel):
    """Structured output from each critic agent."""
    critic: str   # "brand_purist" | "performance_marketer" | "novelty"
    verdict: CriticVerdict
    score: float = Field(ge=0.0, le=100.0)
    reasoning: str
    key_issues: list[str]
    recommendation: str
    # Critic-specific metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


class CritiquePanelLog(BaseModel):
    """The structured debate log produced by the critique panel."""
    round_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    concept_id: str
    votes: list[CriticVote]
    debate_transcript: list[dict[str, str]]  # [{speaker, line}]
    consensus_score: float
    director_synthesis: str
    final_verdict: ConceptStatus


class RationaleDecision(BaseModel):
    """A single traceable design decision linked to a brand rule."""
    decision: str
    rule_text: str
    rule_source: str
    confidence: float = Field(ge=0.0, le=1.0)
    critic_recommendation: str | None = None


class RationaleTrace(BaseModel):
    """Full XDR (Explainable Design Rationale) audit trail."""
    concept_id: str
    concept_name: str
    platform: Platform
    headline: str
    tagline: str
    color_palette: ColorPalette
    layout_spec: LayoutSpec
    decisions: list[RationaleDecision]
    market_signal_hypothesis: str | None = None   # Director's competitive gap analysis
    competitor_gap: str | None = None
    hanlon_reframe: str | None = None  # if prior feedback was reanalyzed
    suggested_iterations: list[str] = Field(default_factory=list)


class EvalScores(BaseModel):
    """Evaluation harness output — every score has a reason."""
    concept_id: str
    brand_fit_score: float = Field(ge=0.0, le=100.0)
    novelty_score: float = Field(ge=0.0, le=100.0)
    predicted_performance_score: float = Field(ge=0.0, le=100.0)
    overall_score: float = Field(ge=0.0, le=100.0)
    # Explainability
    brand_fit_reason: str
    novelty_reason: str
    predicted_perf_reason: str
    # Raw metrics for logging
    embedding_distance_to_centroid: float | None = None
    embedding_distance_to_history: float | None = None
    xgb_ctr_prediction: float | None = None


class GenTask(BaseModel):
    """Input to the generation router."""
    concept_id: str
    prompt: str
    layout_spec: LayoutSpec
    brand_id: str
    needs_brand_typography: bool = False
    budget_tier: str = "standard"   # "draft" | "standard" | "premium"
    requires_licensing_safety: bool = True
    platform: Platform
    backend_override: GenerationBackend | None = None


class TasteVector(BaseModel):
    """Per-brand learned taste vector — updated from feedback signals."""
    brand_id: str
    vector: list[float]   # dense embedding (e.g. 1024-dim voyage-3)
    learning_rate: float = 0.05
    total_signals: int = 0
    last_updated: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Top-level LangGraph State (Pydantic v2 with strict typing)
# ─────────────────────────────────────────────────────────────────────────────

class DesignState(BaseModel):
    """
    The canonical shared state passed between every node in the LangGraph.
    Every field is typed — no free text blobs passed between agents.
    """
    # ── Identity ──────────────────────────────────────────────────────────────
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    brand_id: str
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # ── Brief ─────────────────────────────────────────────────────────────────
    brief: str
    platform: Platform
    tone: ToneProfile
    uploaded_asset_keys: list[str] = Field(default_factory=list)  # S3 keys

    # ── Retrieved context ─────────────────────────────────────────────────────
    brand_rules: list[BrandRule] = Field(default_factory=list)
    moodboard_ids: list[str] = Field(default_factory=list)
    moodboard_descriptions: list[str] = Field(default_factory=list)

    # ── Director output ───────────────────────────────────────────────────────
    creative_strategy: str = ""          # Director's enriched brief
    spawned_agents: list[str] = Field(default_factory=list)
    market_signal_hypothesis: str = ""

    # ── Designer output ───────────────────────────────────────────────────────
    concepts: list[dict[str, Any]] = Field(default_factory=list)   # raw concept dicts
    layout_spec: LayoutSpec | None = None
    gen_task: GenTask | None = None
    generated_image_url: str | None = None

    # ── Critique panel output ─────────────────────────────────────────────────
    critique_log: list[CritiquePanelLog] = Field(default_factory=list)

    # ── Eval harness ─────────────────────────────────────────────────────────
    eval_scores: EvalScores | None = None
    rationale: RationaleTrace | None = None

    # ── Taste model ───────────────────────────────────────────────────────────
    taste_vector: TasteVector | None = None
    concept_embedding: list[float] = Field(default_factory=list)

    # ── HITL / flow control ───────────────────────────────────────────────────
    human_approved: bool = False
    human_feedback: str = ""
    iteration: int = 0
    max_iterations: int = 3
    status: ConceptStatus = ConceptStatus.DRAFT

    model_config = {"arbitrary_types_allowed": True}


# ─────────────────────────────────────────────────────────────────────────────
# API request / response schemas
# ─────────────────────────────────────────────────────────────────────────────

class BriefRequest(BaseModel):
    brand_id: str
    brief: str
    platform: Platform
    tone: ToneProfile
    uploaded_asset_keys: list[str] = Field(default_factory=list)


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress_pct: float = 0.0
    current_agent: str | None = None
    spawned_agents: list[str] = Field(default_factory=list)
    critique_log: CritiquePanelLog | None = None
    eval_scores: EvalScores | None = None
    rationale: RationaleTrace | None = None
    generated_image_url: str | None = None
    error: str | None = None


class HumanFeedbackRequest(BaseModel):
    job_id: str
    approved: bool
    feedback: str = ""


class BrandIngestionRequest(BaseModel):
    brand_id: str
    brand_name: str
    s3_keys: list[str]   # uploaded files


class TasteSignalRequest(BaseModel):
    brand_id: str
    concept_id: str
    reward: float = Field(ge=-1.0, le=1.0)  # -1 rejected, +1 approved, float for perf
