# Adversaria AI: Architectural Decisions (XDR)

## Overview
Adversaria AI is an adversarial multi-agent creative-reasoning engine designed to automate and scale the creative workflow for brand-compliant, high-performance assets. This document outlines the rationale behind our core architectural decisions, prioritizing reliability, explainability, and observability over raw complexity.

## 1. Adversarial Debate & LangGraph Orchestration
**Why Adversarial Debate?**
Instead of a single generative LLM attempting to satisfy competing constraints (e.g., brand purity vs. conversion rate), we use a structured adversarial loop. Three specialized critics (Brand Purist, Performance Marketer, Novelty) evaluate the design space independently. This prevents "averaging out" the creativity and ensures constraints are rigorously enforced. 

**Why LangGraph?**
LangGraph provides cyclic graph orchestration which is essential for iterative design. Standard linear pipelines (like basic LangChain Chains) cannot handle feedback loops efficiently. By modeling the workflow as a `StateGraph`, we gain state persistence (via Postgres checkpointing), enabling Human-in-the-Loop (HITL) approval without tying up compute resources.

## 2. Structured Agent Outputs (Pydantic & Instructor)
**Why Structured Outputs?**
LLMs are prone to hallucinating formats. By enforcing strict `Pydantic` schemas at every node (via structured output parsing), we guarantee type safety across the multi-agent handoffs. This ensures the Senior Designer always receives a valid `LayoutSpec`, and the Router always receives a valid `GenTask`. It prevents pipeline hangs due to malformed text outputs.

## 3. Explainable Design Rationale (XDR)
**Why XDR?**
In enterprise deployments, "black box" generation is unacceptable. Every design decision (color, typography, layout, prompt) is traced back to a specific brand rule or critic recommendation and logged with a confidence score. This trace is persisted in the database and surfaced to the user, allowing them to understand *why* the AI made a specific choice.

## 4. Qdrant RAG Layer for Brand Context
**Why Qdrant?**
Brand guidelines are nuanced and often conflicting. We use Qdrant for vector storage to retrieve highly relevant semantic rules based on the specific brief context (platform, tone). Additionally, it enables "taste signaling" — we store the concept embeddings and update a per-brand taste vector based on historical human feedback (approvals/rejections), allowing the system to learn latent brand preferences over time.

## 5. Model Routing
**Why Multiple Backends?**
We route between Flux Pro, Flux Schnell, SDXL Turbo, ComfyUI, and Adobe Firefly based on the brief's constraints. If a brief requires strict licensing safety, it routes to Firefly. If it requires rapid drafting, it routes to SDXL Turbo. This dynamic routing optimizes cost, latency, and compliance.
