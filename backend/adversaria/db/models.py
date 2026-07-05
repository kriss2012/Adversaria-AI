"""
adversaria/db/models.py — SQLAlchemy 2.0 ORM models (async-ready).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Brand(Base):
    """A brand persona — owns rules, assets, taste vector, and feedback history."""
    __tablename__ = "brands"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    taste_vector: Mapped[list | None] = mapped_column(JSON)  # dense float list
    taste_vector_dim: Mapped[int] = mapped_column(Integer, default=1024)
    taste_signal_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    assets: Mapped[list[BrandAsset]] = relationship("BrandAsset", back_populates="brand", lazy="selectin")
    jobs: Mapped[list[DesignJob]] = relationship("DesignJob", back_populates="brand")
    feedback_entries: Mapped[list[FeedbackEntry]] = relationship("FeedbackEntry", back_populates="brand")


class BrandAsset(Base):
    """Logo, font file, moodboard, or competitor creative stored in S3."""
    __tablename__ = "brand_assets"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(50))  # logo | font | guideline | moodboard | competitor
    filename: Mapped[str] = mapped_column(String(512))
    s3_key: Mapped[str] = mapped_column(String(1024), unique=True)
    mime_type: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    qdrant_ids: Mapped[list | None] = mapped_column(JSON)  # list of Qdrant point IDs after ingestion
    ingested: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    brand: Mapped[Brand] = relationship("Brand", back_populates="assets")


class DesignJob(Base):
    """
    A single pipeline run — from brief submission to final concept.
    LangGraph checkpoints are stored with this job_id as thread_id.
    """
    __tablename__ = "design_jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued")  # ConceptStatus values
    brief: Mapped[str] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(64))
    tone: Mapped[str] = mapped_column(String(64))
    uploaded_asset_keys: Mapped[list | None] = mapped_column(JSON)

    # Agent outputs (stored as JSON blobs for full auditability)
    creative_strategy: Mapped[str | None] = mapped_column(Text)
    spawned_agents: Mapped[list | None] = mapped_column(JSON)
    layout_spec: Mapped[dict | None] = mapped_column(JSON)
    critique_log: Mapped[dict | None] = mapped_column(JSON)    # CritiquePanelLog
    rationale: Mapped[dict | None] = mapped_column(JSON)       # RationaleTrace
    eval_scores: Mapped[dict | None] = mapped_column(JSON)     # EvalScores
    generated_image_url: Mapped[str | None] = mapped_column(String(2048))
    generation_backend: Mapped[str | None] = mapped_column(String(64))

    # HITL
    human_approved: Mapped[bool | None] = mapped_column(Boolean)
    human_feedback: Mapped[str | None] = mapped_column(Text)

    # Meta
    iteration: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    brand: Mapped[Brand] = relationship("Brand", back_populates="jobs")
    feedback_entries: Mapped[list[FeedbackEntry]] = relationship("FeedbackEntry", back_populates="job")


class FeedbackEntry(Base):
    """
    Structured feedback log — feeds the taste model and performance regressor.
    Stores both human signals and external performance data (CTR, engagement).
    """
    __tablename__ = "feedback_entries"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id"), nullable=False, index=True)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("design_jobs.id"), index=True)
    concept_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)

    # Signal type
    signal_type: Mapped[str] = mapped_column(String(32))  # "human_approve" | "human_reject" | "performance"

    # Human signal
    human_approved: Mapped[bool | None] = mapped_column(Boolean)
    human_feedback_text: Mapped[str | None] = mapped_column(Text)

    # Performance signal (from external ad platform API)
    ctr: Mapped[float | None] = mapped_column(Float)
    impressions: Mapped[int | None] = mapped_column(Integer)
    clicks: Mapped[int | None] = mapped_column(Integer)
    conversions: Mapped[int | None] = mapped_column(Integer)
    engagement_rate: Mapped[float | None] = mapped_column(Float)

    # Normalized reward scalar used for taste vector update
    reward: Mapped[float | None] = mapped_column(Float)  # -1.0 to +1.0

    # Concept embedding snapshot (for taste model training)
    concept_embedding: Mapped[list | None] = mapped_column(JSON)

    # Eval scores at the time of feedback (for regression model training)
    brand_fit_score: Mapped[float | None] = mapped_column(Float)
    novelty_score: Mapped[float | None] = mapped_column(Float)
    predicted_performance_score: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    brand: Mapped[Brand] = relationship("Brand", back_populates="feedback_entries")
    job: Mapped[DesignJob | None] = relationship("DesignJob", back_populates="feedback_entries")


class AgentDecisionTrace(Base):
    """
    Fine-grained log of every agent decision — for Langfuse/LangSmith correlation.
    Stores the full input/output of each LangGraph node call.
    """
    __tablename__ = "agent_decision_traces"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("design_jobs.id"), nullable=False, index=True)
    node_name: Mapped[str] = mapped_column(String(128))
    agent_name: Mapped[str] = mapped_column(String(128))
    iteration: Mapped[int] = mapped_column(Integer, default=0)
    input_state_snapshot: Mapped[dict | None] = mapped_column(JSON)
    output_state_snapshot: Mapped[dict | None] = mapped_column(JSON)
    llm_prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    llm_completion_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    langsmith_run_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
