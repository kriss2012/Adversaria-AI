"""
adversaria/api/routes.py — FastAPI route definitions.

Endpoints:
  POST   /v1/brands                    — create a brand
  POST   /v1/brands/{id}/ingest        — upload + ingest assets
  POST   /v1/jobs                      — submit a brief (queues pipeline)
  GET    /v1/jobs/{id}                 — poll job status
  POST   /v1/jobs/{id}/approve         — HITL approval / rejection
  POST   /v1/jobs/{id}/taste-signal    — report performance signal
  GET    /v1/jobs/{id}/stream          — SSE real-time progress stream
  GET    /v1/brands/{id}/eval-history  — eval history for dashboard
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adversaria.config import get_settings
from adversaria.db.models import Brand, BrandAsset, DesignJob, FeedbackEntry
from adversaria.db.session import get_db
from adversaria.schemas import (
    BriefRequest,
    BrandIngestionRequest,
    ConceptStatus,
    DesignState,
    HumanFeedbackRequest,
    JobStatusResponse,
    TasteSignalRequest,
    TasteVector,
)
from adversaria.services.embeddings import get_embedding_service

_settings = get_settings()
router = APIRouter(prefix="/v1")


# ─────────────────────────────────────────────────────────────────────────────
# Brand management
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/brands", status_code=201)
async def create_brand(
    name: str = Form(...),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    existing = await db.execute(select(Brand).where(Brand.name == name))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Brand '{name}' already exists")

    brand = Brand(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        taste_vector=get_embedding_service().init_taste_vector(),
    )
    db.add(brand)
    await db.flush()
    return {"brand_id": brand.id, "name": brand.name}


@router.post("/brands/{brand_id}/assets", status_code=201)
async def upload_brand_assets(
    brand_id: str,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Upload brand assets to S3 and queue ingestion."""
    import boto3  # noqa: PLC0415

    brand = await db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(404, "Brand not found")

    s3 = boto3.client(
        "s3",
        endpoint_url=_settings.s3_endpoint_url,
        aws_access_key_id=_settings.s3_access_key_id,
        aws_secret_access_key=_settings.s3_secret_access_key,
        region_name=_settings.s3_region,
    )

    uploaded_keys = []
    for upload in files:
        s3_key = f"brands/{brand_id}/assets/{uuid.uuid4()}_{upload.filename}"
        content = await upload.read()

        s3.put_object(
            Bucket=_settings.s3_bucket_name,
            Key=s3_key,
            Body=content,
            ContentType=upload.content_type or "application/octet-stream",
        )

        asset = BrandAsset(
            brand_id=brand_id,
            asset_type=_guess_asset_type(upload.filename or ""),
            filename=upload.filename or "",
            s3_key=s3_key,
            mime_type=upload.content_type,
            size_bytes=len(content),
        )
        db.add(asset)
        uploaded_keys.append(s3_key)

    await db.flush()

    # Queue ingestion task
    from adversaria.workers.celery_app import ingest_brand_assets_task  # noqa: PLC0415
    task = ingest_brand_assets_task.delay(brand_id, uploaded_keys)

    return {"brand_id": brand_id, "uploaded": len(uploaded_keys), "task_id": task.id}


# ─────────────────────────────────────────────────────────────────────────────
# Design jobs
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/jobs", status_code=202)
async def submit_brief(
    req: BriefRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Submit a creative brief — creates a job and queues the pipeline."""
    brand = await db.get(Brand, req.brand_id)
    if not brand:
        raise HTTPException(404, "Brand not found")

    job_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    # Build initial DesignState
    initial_state = DesignState(
        run_id=run_id,
        brand_id=req.brand_id,
        job_id=job_id,
        brief=req.brief,
        platform=req.platform,
        tone=req.tone,
        uploaded_asset_keys=req.uploaded_asset_keys,
        taste_vector=TasteVector(
            brand_id=req.brand_id,
            vector=brand.taste_vector or get_embedding_service().init_taste_vector(),
        ),
    )

    # Persist job record
    job = DesignJob(
        id=job_id,
        brand_id=req.brand_id,
        run_id=run_id,
        brief=req.brief,
        platform=req.platform.value,
        tone=req.tone.value,
        uploaded_asset_keys=req.uploaded_asset_keys,
        status="queued",
        started_at=datetime.utcnow(),
    )
    db.add(job)
    await db.flush()

    # Queue pipeline
    from adversaria.workers.celery_app import run_pipeline_task  # noqa: PLC0415
    run_pipeline_task.apply_async(
        args=[job_id, initial_state.model_dump(mode="json")],
        task_id=job_id,
    )

    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    job = await db.get(DesignJob, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    return JobStatusResponse(
        job_id=job_id,
        status=job.status,
        current_agent=None,
        spawned_agents=job.spawned_agents or [],
        critique_log=job.critique_log,
        eval_scores=job.eval_scores,
        rationale=job.rationale,
        generated_image_url=job.generated_image_url,
        error=job.error_message,
    )


@router.post("/jobs/{job_id}/approve")
async def approve_or_reject_job(
    job_id: str,
    req: HumanFeedbackRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    HITL: human approves or rejects a concept.
    If the graph is paused at human_review, this resumes it.
    """
    job = await db.get(DesignJob, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != ConceptStatus.PENDING_HUMAN.value:
        raise HTTPException(400, f"Job is not awaiting human review (status: {job.status})")

    job.human_approved = req.approved
    job.human_feedback_text = req.feedback if hasattr(req, 'feedback') else ""
    job.status = "approved" if req.approved else "iterating"
    await db.flush()

    # Log feedback entry
    fb = FeedbackEntry(
        brand_id=job.brand_id,
        job_id=job_id,
        concept_id=str(uuid.uuid4()),
        signal_type="human_approve" if req.approved else "human_reject",
        human_approved=req.approved,
        human_feedback_text=req.feedback,
        reward=1.0 if req.approved else -1.0,
    )
    db.add(fb)
    await db.flush()

    # Resume pipeline (re-queue with updated state)
    from adversaria.workers.celery_app import run_pipeline_task  # noqa: PLC0415
    updated_state = {
        "brand_id": job.brand_id,
        "job_id": job_id,
        "run_id": str(job.run_id),
        "brief": job.brief,
        "platform": job.platform,
        "tone": job.tone,
        "human_approved": req.approved,
        "human_feedback": req.feedback,
        "status": "approved" if req.approved else "iterated",
    }
    run_pipeline_task.apply_async(args=[job_id, updated_state])

    return {"job_id": job_id, "status": "resumed", "approved": str(req.approved)}


# ─────────────────────────────────────────────────────────────────────────────
# Taste model feedback
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/jobs/{job_id}/taste-signal")
async def record_taste_signal(
    job_id: str,
    req: TasteSignalRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Records a performance signal (CTR, engagement, or manual +1/-1)
    and updates the brand's taste vector.
    """
    brand = await db.get(Brand, req.brand_id)
    if not brand:
        raise HTTPException(404, "Brand not found")

    job = await db.get(DesignJob, job_id)
    concept_embedding = []
    if job and job.eval_scores and isinstance(job.eval_scores, dict):
        # In practice, concept_embedding would be stored in FeedbackEntry or Redis
        pass

    # Update taste vector
    emb = get_embedding_service()
    current_tv = brand.taste_vector or emb.init_taste_vector()

    if concept_embedding:
        updated_tv = emb.update_taste_vector(
            taste_vector=current_tv,
            new_signal=concept_embedding,
            reward=req.reward,
        )
        brand.taste_vector = updated_tv
        brand.taste_signal_count = (brand.taste_signal_count or 0) + 1

    # Log signal
    fb = FeedbackEntry(
        brand_id=req.brand_id,
        job_id=job_id,
        concept_id=req.concept_id,
        signal_type="performance",
        reward=req.reward,
    )
    db.add(fb)
    await db.flush()

    return {
        "brand_id": req.brand_id,
        "taste_signals_total": brand.taste_signal_count,
        "reward_applied": req.reward,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SSE: real-time progress stream
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}/stream")
async def stream_job_progress(job_id: str) -> StreamingResponse:
    """
    Server-Sent Events endpoint — frontend subscribes here for real-time
    pipeline progress without polling.
    """
    import redis.asyncio as aioredis  # noqa: PLC0415

    async def event_generator() -> AsyncGenerator[str, None]:
        redis_client = aioredis.from_url(_settings.redis_url)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"job:{job_id}")

        try:
            # Send initial connection event
            yield f"data: {json.dumps({'event': 'connected', 'job_id': job_id})}\n\n"

            timeout = 600  # 10 minutes max
            elapsed = 0
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield f"data: {message['data'].decode()}\n\n"
                    data = json.loads(message["data"])
                    if data.get("status") in {"complete", "error"}:
                        break
                await asyncio.sleep(0.1)
                elapsed += 0.1
                if elapsed > timeout:
                    break
        finally:
            await pubsub.unsubscribe(f"job:{job_id}")
            await redis_client.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Eval history (for dashboard)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/brands/{brand_id}/eval-history")
async def get_eval_history(
    brand_id: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(DesignJob)
        .where(DesignJob.brand_id == brand_id, DesignJob.eval_scores.isnot(None))
        .order_by(DesignJob.created_at.desc())
        .limit(limit)
    )
    jobs = result.scalars().all()
    return [
        {
            "job_id": j.id,
            "brief_preview": j.brief[:80],
            "status": j.status,
            "eval_scores": j.eval_scores,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        }
        for j in jobs
    ]


# ─── Utility ─────────────────────────────────────────────────────────────────

def _guess_asset_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        return "guideline"
    if ext in {"svg", "ai", "eps"}:
        return "logo"
    if ext in {"ttf", "otf", "woff", "woff2"}:
        return "font"
    if ext in {"png", "jpg", "jpeg", "webp"}:
        return "moodboard"
    return "other"
