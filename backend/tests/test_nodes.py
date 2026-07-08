"""
tests/test_nodes.py — Unit tests for each LangGraph agent node.

Uses pytest-asyncio + unittest.mock to isolate every node from external APIs.
Run: pytest tests/ -v

Design principle: test the *contract* of each node (inputs → outputs shape),
not the LLM output content (which is non-deterministic).
"""
from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adversaria.schemas import (
    BrandRule,
    ColorPalette,
    ConceptStatus,
    CritiquePanelLog,
    CriticVerdict,
    CriticVote,
    DesignState,
    EvalScores,
    GenTask,
    LayoutSpec,
    Platform,
    ToneProfile,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_state(**overrides: Any) -> DesignState:
    defaults: dict[str, Any] = {
        "brand_id": "test-brand-001",
        "job_id": str(uuid.uuid4()),
        "brief": "Design a high-impact gym wear Instagram ad for AuraFit.",
        "platform": Platform.INSTAGRAM_FEED,
        "tone": ToneProfile.ENERGETIC,
        "brand_rules": [
            {
                "rule_id": str(uuid.uuid4()),
                "rule_type": "color",
                "rule_text": "Primary color is violet #7C3AED",
                "source_file": "brand_guidelines.pdf",
                "confidence": 0.95,
                "embedding_distance": 0.12,
            }
        ],
        "iteration": 0,
        "max_iterations": 3,
    }
    defaults.update(overrides)
    return DesignState(**defaults)


def _make_layout() -> LayoutSpec:
    return LayoutSpec(
        canvas_width=1080,
        canvas_height=1080,
        product_area_pct=0.4,
        headline_position="top_left",
        cta_position="bottom_center",
        logo_position="bottom_left",
        typeface_primary="Space Grotesk 700",
        color_palette=ColorPalette(
            primary="#7C3AED", secondary="#06b6d4",
            accent="#f59e0b", background="#0F172A", text="#F1F5F9",
        ),
        background_style="dark_gradient",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test: creative_director_node
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_creative_director_returns_strategy():
    """Director node must return creative_strategy, spawned_agents, market_signal_hypothesis."""
    from adversaria.agents.nodes import DirectorOutput

    mock_output = DirectorOutput(
        creative_strategy="High-contrast neon gym aesthetic targeting Gen Z.",
        spawned_agents=["MarketSignal"],
        market_signal_hypothesis="Competitors lack kinetic typography.",
        key_constraints=["Must use violet primary", "No competitor logos"],
    )

    with patch("adversaria.agents.nodes._llm") as mock_llm_fn:
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_output)
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_chain
        mock_llm_fn.return_value = mock_llm

        from adversaria.agents.nodes import creative_director_node
        state = _make_state()
        result = await creative_director_node(state)

    assert "creative_strategy" in result
    assert isinstance(result["creative_strategy"], str)
    assert len(result["creative_strategy"]) > 0
    assert "spawned_agents" in result
    assert isinstance(result["spawned_agents"], list)
    assert "market_signal_hypothesis" in result


# ─────────────────────────────────────────────────────────────────────────────
# Test: senior_designer_node
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_senior_designer_returns_concept_and_gentask():
    """Designer node must return concepts list, layout_spec dict, and gen_task dict."""
    from adversaria.agents.nodes import DesignerOutput

    mock_output = DesignerOutput(
        concept_name="Neon Surge",
        headline="Fuel Your Fire",
        tagline="Premium gym wear for the relentless.",
        cta_text="Shop Now",
        layout_spec={
            "canvas_width": 1080,
            "canvas_height": 1080,
            "product_area_pct": 0.45,
            "headline_position": "top_left",
            "cta_position": "bottom_center",
            "logo_position": "bottom_left",
            "typeface_primary": "Space Grotesk 700",
            "background_style": "dark_gradient",
            "color_palette": {
                "primary": "#7C3AED", "secondary": "#06b6d4",
                "accent": "#f59e0b", "background": "#0F172A", "text": "#F1F5F9",
            },
        },
        generation_prompt="Neon gym product photo with violet glow effects.",
        needs_brand_typography=False,
        requires_licensing_safety=True,
    )

    with patch("adversaria.agents.nodes._llm") as mock_llm_fn:
        mock_chain = AsyncMock()
        mock_chain.ainvoke = AsyncMock(return_value=mock_output)
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_chain
        mock_llm_fn.return_value = mock_llm

        from adversaria.agents.nodes import senior_designer_node
        state = _make_state(creative_strategy="High-contrast neon gym aesthetic.")
        result = await senior_designer_node(state)

    assert "concepts" in result
    assert len(result["concepts"]) == 1
    c = result["concepts"][0]
    assert "id" in c and "headline" in c and "layout_spec" in c

    assert "gen_task" in result
    gt = result["gen_task"]
    assert "concept_id" in gt and "prompt" in gt

    assert "layout_spec" in result


# ─────────────────────────────────────────────────────────────────────────────
# Test: critique_panel_node — consensus score calibration
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_critique_panel_calibrated_consensus():
    """
    Consensus score must be penalised when critics strongly disagree.
    Three critics scoring 90, 50, 30 (std ≈ 30) should produce a consensus
    lower than the raw mean (56.7).
    """
    from adversaria.agents.nodes import (
        CriticOutput,
        SynthesisOutput,
        critique_panel_node,
    )

    critic_scores = [90.0, 50.0, 30.0]

    def _make_critic_output(score: float) -> CriticOutput:
        return CriticOutput(
            verdict="amend",
            score=score,
            reasoning="Test reasoning",
            key_issues=["Issue A"],
            recommendation="Fix it",
        )

    mock_synth = SynthesisOutput(
        director_synthesis="Mixed panel — iterate on brand compliance.",
        final_verdict="iterated",
        debate_transcript=[{"speaker": "Director", "line": "Iterate."}],
    )

    call_count = 0

    async def mock_ainvoke(messages):
        nonlocal call_count
        call_count += 1
        if call_count <= 3:
            return _make_critic_output(critic_scores[call_count - 1])
        return mock_synth

    with patch("adversaria.agents.nodes._llm") as mock_llm_fn:
        mock_chain = AsyncMock()
        mock_chain.ainvoke = mock_ainvoke
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_chain
        mock_llm_fn.return_value = mock_llm

        concept_id = str(uuid.uuid4())
        state = _make_state(
            concepts=[{
                "id": concept_id,
                "name": "Test",
                "headline": "Test",
                "tagline": "test",
                "cta_text": "Go",
                "layout_spec": _make_layout().model_dump(),
            }]
        )
        result = await critique_panel_node(state)

    raw_mean = sum(critic_scores) / len(critic_scores)
    last_critique = result["critique_log"][-1]
    consensus = last_critique["consensus_score"]

    # Calibrated score must be BELOW raw mean due to disagreement penalty
    assert consensus < raw_mean, (
        f"Expected calibrated consensus {consensus} < raw mean {raw_mean}"
    )
    # Iteration counter must have incremented (ITERATED verdict)
    assert result["iteration"] == 1


@pytest.mark.asyncio
async def test_critique_panel_increments_iteration_on_iterated():
    """state.iteration must increment exactly once on ITERATED verdict."""
    from adversaria.agents.nodes import CriticOutput, SynthesisOutput, critique_panel_node

    mock_synth = SynthesisOutput(
        director_synthesis="Keep iterating.",
        final_verdict="iterated",
        debate_transcript=[],
    )
    call_count = 0

    async def mock_ainvoke(messages):
        nonlocal call_count
        call_count += 1
        if call_count <= 3:
            return CriticOutput(verdict="amend", score=70.0, reasoning="r",
                                key_issues=[], recommendation="fix")
        return mock_synth

    with patch("adversaria.agents.nodes._llm") as mock_llm_fn:
        mock_chain = AsyncMock()
        mock_chain.ainvoke = mock_ainvoke
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_chain
        mock_llm_fn.return_value = mock_llm

        concept_id = str(uuid.uuid4())
        state = _make_state(
            iteration=2,
            concepts=[{
                "id": concept_id, "name": "T", "headline": "T",
                "tagline": "t", "cta_text": "g",
                "layout_spec": _make_layout().model_dump(),
            }]
        )
        result = await critique_panel_node(state)

    assert result["iteration"] == 3


@pytest.mark.asyncio
async def test_critique_panel_no_increment_on_approved():
    """state.iteration must NOT increment when critics approve."""
    from adversaria.agents.nodes import CriticOutput, SynthesisOutput, critique_panel_node

    mock_synth = SynthesisOutput(
        director_synthesis="Approved.",
        final_verdict="approved",
        debate_transcript=[],
    )
    call_count = 0

    async def mock_ainvoke(messages):
        nonlocal call_count
        call_count += 1
        if call_count <= 3:
            return CriticOutput(verdict="approve", score=88.0, reasoning="r",
                                key_issues=[], recommendation="none")
        return mock_synth

    with patch("adversaria.agents.nodes._llm") as mock_llm_fn:
        mock_chain = AsyncMock()
        mock_chain.ainvoke = mock_ainvoke
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_chain
        mock_llm_fn.return_value = mock_llm

        state = _make_state(
            iteration=1,
            concepts=[{
                "id": str(uuid.uuid4()), "name": "T", "headline": "T",
                "tagline": "t", "cta_text": "g",
                "layout_spec": _make_layout().model_dump(),
            }]
        )
        result = await critique_panel_node(state)

    assert result["iteration"] == 1  # unchanged


# ─────────────────────────────────────────────────────────────────────────────
# Test: max_iterations cap in graph routing
# ─────────────────────────────────────────────────────────────────────────────

def test_route_after_critique_forces_human_review_at_max():
    """When iteration >= max_iterations, routing must go to human_review regardless of verdict."""
    from adversaria.agents.graph import route_after_critique

    state = _make_state(
        iteration=3,
        max_iterations=3,
        critique_log=[{
            "round_id": str(uuid.uuid4()),
            "concept_id": str(uuid.uuid4()),
            "final_verdict": ConceptStatus.ITERATED.value,
            "consensus_score": 75,
            "director_synthesis": "Keep going",
            "votes": [],
            "debate_transcript": [],
        }],
    )
    assert route_after_critique(state) == "human_review"


def test_route_after_critique_approves_high_confidence():
    """High confidence approval (>=80) routes to eval, skipping HITL."""
    from adversaria.agents.graph import route_after_critique

    state = _make_state(
        iteration=0,
        critique_log=[{
            "round_id": str(uuid.uuid4()),
            "concept_id": str(uuid.uuid4()),
            "final_verdict": ConceptStatus.APPROVED.value,
            "consensus_score": 88,
            "director_synthesis": "Approved.",
            "votes": [],
            "debate_transcript": [],
        }],
    )
    assert route_after_critique(state) == "eval_harness"


# ─────────────────────────────────────────────────────────────────────────────
# Test: cost_usd helper
# ─────────────────────────────────────────────────────────────────────────────

def test_cost_usd_haiku():
    from adversaria.agents.nodes import _cost_usd
    cost = _cost_usd("claude-haiku-4-5", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    # 1M input @ $0.25 + 1M output @ $1.25 = $1.50
    assert abs(cost - 1.50) < 0.001


def test_cost_usd_opus():
    from adversaria.agents.nodes import _cost_usd
    cost = _cost_usd("claude-opus-4-5", prompt_tokens=100_000, completion_tokens=10_000)
    # 100k input @ $15/M = $1.50, 10k output @ $75/M = $0.75 → $2.25
    assert abs(cost - 2.25) < 0.001


# ─────────────────────────────────────────────────────────────────────────────
# Test: human_review_node
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_human_review_sets_pending_status():
    from adversaria.agents.nodes import human_review_node
    state = _make_state()
    result = await human_review_node(state)
    assert result["status"] == ConceptStatus.PENDING_HUMAN
