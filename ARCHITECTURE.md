# Adversaria AI — Architecture & Design Decisions

> **Audience:** Technical reviewers, judges, and engineers doing due diligence.  
> This document explains *why* we made each architectural choice, not just what exists.

---

## System Overview

Adversaria is an **adversarial multi-agent creative reasoning engine**. A single LLM prompt cannot simultaneously optimise for brand compliance, conversion rate, and creative novelty — these objectives actively conflict. We resolve the conflict via a structured adversarial debate panel.

```
Brief Input
    │
    ▼
retrieve_brand_context  ── Qdrant RAG (semantic brand rule retrieval)
    │
    ▼
creative_director       ── Claude Opus: enriched strategy, spawns sub-agents
    │
    ▼
senior_designer         ── Claude Sonnet: structured LayoutSpec (Pydantic)
    │
    ▼
generate_image          ── Dynamic router: Flux / SDXL / Firefly / ComfyUI
    │
    ▼
critique_panel ◄────────── 3 Critics in parallel (asyncio.gather):
    │                         Brand Purist | Performance Marketer | Novelty
    │                      Director synthesises → calibrated consensus score
    │
    ├── APPROVED (score ≥ 80) ──► eval_harness ──► build_rationale ──► END
    ├── ITERATED (score 60–79) ──► senior_designer  [loop, max 3 iterations]
    └── LOW CONFIDENCE (<60) ──► human_review (HITL pause)
```

---

## Key Design Decisions

### 1. Why Adversarial Debate Instead of a Single Prompt?

A single LLM balancing three conflicting objectives (brand fidelity vs. CTR vs. novelty) will compromise on all three. We assign exclusive optimisation targets to independent critics — the Brand Purist has never seen a conversion metric; it only enforces brand rules. This replicates how real creative teams work: the brand manager and the performance marketer argue, and the Creative Director arbitrates.

**Reliability note:** The debate loop has a hard `max_iterations=3` cap (default). The routing function checks `state.iteration >= state.max_iterations` *before* reading the critique verdict, so a pathological critique loop is unconditionally bounded. `state.iteration` is incremented inside `critique_panel_node` on every `ITERATED` verdict — not in the router — so the counter is grounded to actual loop iterations.

### 2. Structured Outputs via Pydantic + LangChain

Every agent node uses `ChatAnthropic.with_structured_output(PydanticModel)`. This is not cosmetic — it means:
- The LLM is constrained to output a schema the next node can instantiate without `json.loads` fragility.
- Malformed outputs raise a `ValidationError` that tenacity retries automatically (3 attempts, exponential backoff).
- The inter-node contracts are statically typed and testable without running the actual LLM.

### 3. Confidence Score Calibration

The `consensus_score` shown in the UI is **not the model's self-reported confidence**. It is computed as:

```python
mean_score = mean(critic_scores)            # e.g. 56.7 for [90, 50, 30]
std_dev    = stdev(critic_scores)           # e.g. 30.0
disagreement_penalty = min(25, std_dev * 0.5)   # e.g. 15.0
consensus_score = mean_score - disagreement_penalty   # e.g. 41.7
```

High inter-critic disagreement (high std dev) is penalised. This grounds the score in measurable inter-agent agreement, not a hallucinated certainty number.

### 4. Why LangGraph?

Standard LangChain chains are DAGs — they cannot express the `senior_designer → critique → senior_designer` feedback loop. LangGraph's `StateGraph` natively supports cycles with typed state. The Postgres checkpointer (`AsyncPostgresSaver`) persists graph state at the `human_review` node, enabling HITL approval hours after the initial run without holding a process open.

### 5. Why Qdrant for RAG?

Brand guidelines are not keyword-searchable — "use the brand voice" means nothing without semantic context about what that voice is. Qdrant stores dense Voyage AI embeddings of each semantic brand rule chunk and retrieves the top-12 most relevant rules given the specific brief. It also stores historical concept embeddings, enabling the novelty score (cosine distance from the brand's past approved work) and the taste vector update.

### 6. Cost Tracking

The `_cost_usd()` helper in `nodes.py` uses official Anthropic list pricing:

| Model | Input $/1M | Output $/1M |
|---|---|---|
| claude-opus-4-5 | $15.00 | $75.00 |
| claude-sonnet-4-5 | $3.00 | $15.00 |
| claude-haiku-4-5 | $0.25 | $1.25 |

Token counts are available from every `langchain-anthropic` response via `AIMessage.usage_metadata`. These are persisted to `AgentDecisionTrace.llm_prompt_tokens` / `llm_completion_tokens`, and cost is surfaced in the API response. The `AgentDecisionTrace` table is populated per node call, giving a full cost breakdown per pipeline run.

### 7. Security Model

- **JWT enforcement:** All 9 routes require a valid `HS256` JWT Bearer token via `get_current_user`. The `/health` endpoint is exempt (monitoring probes).
- **Rate limiting via slowapi:** Generation endpoints (`/jobs`, `/jobs/{id}/inpaint`) are capped at 10 and 5 req/min per IP respectively. LLM + image gen is the expensive attack surface.
- **No secrets in code:** All credentials are loaded from environment variables via `pydantic-settings`.

### 8. Test Strategy

```
tests/
  conftest.py       — env stubs, prevents real API calls
  test_nodes.py     — unit tests per node with mocked LLM
```

Every node test mocks `_llm()` and validates the *output contract* (key presence, type, range), not LLM content (non-deterministic). Routing logic (`route_after_critique`) is tested with constructed state objects — no LLM needed.

Run: `cd backend && pytest tests/ -v`

---

## What's Not Yet Production-Ready

1. **XGBoost performance model**: Falls back to the calibrated heuristic until 50+ feedback entries exist to train on.
2. **LangSmith tracing**: `LANGCHAIN_API_KEY` must be set for distributed trace correlation across nodes.
3. **Alembic migrations**: `create_tables()` is used in development; production deployments need `alembic upgrade head`.
