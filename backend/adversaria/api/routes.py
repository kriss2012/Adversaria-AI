"""
adversaria/api/routes.py — FastAPI route definitions.

Endpoints:
  POST   /v1/brands                    — create a brand
  POST   /v1/brands/{id}/assets        — upload + ingest brand assets
  POST   /v1/jobs                      — submit a brief (queues pipeline)
  GET    /v1/jobs/{id}                 — poll job status
  POST   /v1/jobs/{id}/approve         — HITL approval / rejection
  POST   /v1/jobs/{id}/taste-signal    — report performance signal
  POST   /v1/jobs/{id}/inpaint         — localized regeneration (mask one element)
  GET    /v1/jobs/{id}/stream          — SSE real-time progress stream
  GET    /v1/brands/{id}/eval-history  — eval history for dashboard

Security:
  - JWT Bearer enforced on every route via get_current_user dependency
  - Rate limiting via slowapi: 10 req/min on generation, 60/min on reads
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from pydantic import BaseModel
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
    Platform,
    TasteSignalRequest,
    TasteVector,
)
from adversaria.services.embeddings import get_embedding_service
from adversaria.services.generation_router import get_generation_router, PLATFORM_SPECS

_settings = get_settings()
router = APIRouter(prefix="/v1")

# ── Auth ───────────────────────────────────────────────────────────────────────
_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    """Decode and validate JWT. Raises 401 on any failure."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            _settings.jwt_secret,
            algorithms=[_settings.jwt_algorithm],
        )
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=401, detail="Token missing 'sub' claim")
        return sub
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}") from exc


# ── Rate limiter ───────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


# ─────────────────────────────────────────────────────────────────────────────
# Brand management
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/brands", status_code=201)
@limiter.limit("20/minute")
async def create_brand(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
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
@limiter.limit("10/minute")
async def upload_brand_assets(
    request: Request,
    brand_id: str,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
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

    # Queue ingestion task using unified task dispatcher
    from adversaria.services.tasks import dispatch_ingest_brand_assets  # noqa: PLC0415
    task_id = dispatch_ingest_brand_assets(brand_id, uploaded_keys)

    return {"brand_id": brand_id, "uploaded": len(uploaded_keys), "task_id": task_id}


# ─────────────────────────────────────────────────────────────────────────────
# Design jobs
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/jobs", status_code=202)
async def submit_brief(
    req: BriefRequest,
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
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

    # Queue pipeline using unified task dispatcher
    from adversaria.services.tasks import dispatch_run_pipeline  # noqa: PLC0415
    dispatch_run_pipeline(job_id, initial_state.model_dump(mode="json"))

    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
@limiter.limit("60/minute")
async def get_job_status(
    request: Request,
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> JobStatusResponse:
    # Check inpaint task cache first
    from adversaria.services.pubsub import get_cache  # noqa: PLC0415
    inpaint_data = await get_cache(f"inpaint:{job_id}")
    if inpaint_data:
        return JobStatusResponse(
            job_id=job_id,
            status=inpaint_data.get("status", "queued"),
            current_agent="inpaint",
            spawned_agents=[],
            generated_image_url=inpaint_data.get("generated_image_url"),
            error=inpaint_data.get("error"),
        )

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
@limiter.limit("30/minute")
async def approve_or_reject_job(
    request: Request,
    job_id: str,
    req: HumanFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
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
    job.human_feedback = req.feedback
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

    # Resume pipeline using unified task dispatcher (re-queue with updated state)
    from adversaria.services.tasks import dispatch_run_pipeline  # noqa: PLC0415
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
    dispatch_run_pipeline(job_id, updated_state)

    return {"job_id": job_id, "status": "resumed", "approved": str(req.approved)}


# ─────────────────────────────────────────────────────────────────────────────
# Taste model feedback
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/jobs/{job_id}/taste-signal")
@limiter.limit("30/minute")
async def record_taste_signal(
    request: Request,
    job_id: str,
    req: TasteSignalRequest,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Records a performance signal (CTR, engagement, or manual +1/-1)
    and updates the brand's taste vector using the concept embedding
    stored when eval_harness ran.
    """
    brand = await db.get(Brand, req.brand_id)
    if not brand:
        raise HTTPException(404, "Brand not found")

    job = await db.get(DesignJob, job_id)
    concept_embedding: list[float] = []

    # Retrieve concept_embedding stored in FeedbackEntry from the approve/reject call,
    # or fall back to a text embedding of the concept's headline from eval_scores.
    if job and job.eval_scores and isinstance(job.eval_scores, dict):
        # The eval_harness node stores concept_embedding in DesignState;
        # the Celery task persists eval_scores to the job.  If we stored the
        # embedding alongside eval_scores, retrieve it here.
        concept_embedding = job.eval_scores.get("concept_embedding", [])

    if not concept_embedding and job and job.brief:
        # Fallback: embed the brief as a proxy for the concept vector
        emb_service = get_embedding_service()
        concept_embedding = await emb_service.embed_query(job.brief)

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

    # Log signal with the embedding snapshot for future XGBoost retraining
    fb = FeedbackEntry(
        brand_id=req.brand_id,
        job_id=job_id,
        concept_id=req.concept_id,
        signal_type="performance",
        reward=req.reward,
        concept_embedding=concept_embedding if concept_embedding else None,
        brand_fit_score=job.eval_scores.get("brand_fit_score") if job and job.eval_scores else None,
        novelty_score=job.eval_scores.get("novelty_score") if job and job.eval_scores else None,
        predicted_performance_score=job.eval_scores.get("predicted_performance_score") if job and job.eval_scores else None,
    )
    db.add(fb)
    await db.flush()

    return {
        "brand_id": req.brand_id,
        "taste_signals_total": brand.taste_signal_count,
        "reward_applied": req.reward,
        "embedding_captured": bool(concept_embedding),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SSE: real-time progress stream
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}/stream")
@limiter.limit("20/minute")
async def stream_job_progress(
    request: Request,
    job_id: str,
    _user: str = Depends(get_current_user),
) -> StreamingResponse:
    """
    Server-Sent Events endpoint — frontend subscribes here for real-time
    pipeline progress without polling.
    """
    import redis.asyncio as aioredis  # noqa: PLC0415

    async def event_generator() -> AsyncGenerator[str, None]:
        from adversaria.services.pubsub import subscribe_channel  # noqa: PLC0415
        try:
            # Send initial connection event
            yield f"data: {json.dumps({'event': 'connected', 'job_id': job_id})}\n\n"

            timeout = 600  # 10 minutes max
            elapsed = 0
            async for message in subscribe_channel(f"job:{job_id}"):
                yield f"data: {message}\n\n"
                data = json.loads(message)
                if data.get("status") in {"complete", "error"}:
                    break
                await asyncio.sleep(0.1)
                elapsed += 0.1
                if elapsed > timeout:
                    break
        except Exception:
            pass

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
@limiter.limit("30/minute")
async def get_eval_history(
    request: Request,
    brand_id: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
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


# ────────────────────────────────────────────────────────────────────────────────
# Localized regeneration (inpainting) — preserves the full composition
# ────────────────────────────────────────────────────────────────────────────────

class InpaintRequest(BaseModel):
    """Request body for localized element regeneration."""
    brand_id: str
    concept_id: str
    nudge_prompt: str   # What to regenerate in the masked region
    platform: Platform
    image_url: str      # The base image to inpaint onto
    mask_url: str       # Black-and-white mask: white = regenerate, black = preserve

    # Import here to avoid circular schema import
    class Config:
        from_attributes = True


@router.post("/jobs/{job_id}/inpaint", status_code=202)
@limiter.limit("5/minute")   # Inpainting is the most expensive endpoint
async def localized_inpaint(
    request: Request,
    job_id: str,
    req: InpaintRequest,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Localized regeneration: nudge a single element in a generated concept
    without rerolling the entire composition.

    The client provides:
      - image_url: the full generated image (from a completed job)
      - mask_url:  a white-on-black mask indicating which region to regenerate
      - nudge_prompt: description of the new element to paint in

    Routes to ComfyUI flux_inpaint workflow.
    Returns immediately with a task_id; poll /v1/jobs/{task_id} for status.
    """
    from adversaria.schemas import GenTask, LayoutSpec, ColorPalette  # noqa: PLC0415
    from adversaria.workers.celery_app import run_inpaint_task  # noqa: PLC0415

    # Build a minimal GenTask so the router can resolve backend + platform spec
    default_palette = ColorPalette(
        primary="#7C3AED", secondary="#06b6d4",
        accent="#f59e0b", background="#0F172A", text="#F1F5F9",
    )
    specs = PLATFORM_SPECS.get(req.platform.value, {"width": 1080, "height": 1080})
    layout = LayoutSpec(
        canvas_width=specs["width"], canvas_height=specs["height"],
        product_area_pct=0.4, headline_position="top_left",
        cta_position="bottom_center", logo_position="bottom_left",
        typeface_primary="Space Grotesk 700",
        color_palette=default_palette, background_style="dark_gradient",
    )
    gen_task = GenTask(
        concept_id=req.concept_id,
        prompt=req.nudge_prompt,
        layout_spec=layout,
        brand_id=req.brand_id,
        needs_brand_typography=False,
        budget_tier="standard",
        requires_licensing_safety=False,
        platform=req.platform,
        backend_override=None,
    )

    inpaint_task_id = str(uuid.uuid4())
    from adversaria.services.tasks import dispatch_run_inpaint  # noqa: PLC0415
    dispatch_run_inpaint(
        inpaint_task_id,
        gen_task.model_dump(mode="json"),
        req.image_url,
        req.mask_url,
    )

    return {
        "task_id": inpaint_task_id,
        "status": "queued",
        "message": "Inpainting queued — poll /v1/jobs/{task_id} for the output URL",
    }
