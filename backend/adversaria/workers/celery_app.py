"""
adversaria/workers/celery_app.py — Celery configuration and task definitions.

Image generation and long pipeline runs are dispatched here — never block
the FastAPI request thread.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from celery import Celery
from celery.utils.log import get_task_logger

from adversaria.config import get_settings

_settings = get_settings()
logger = get_task_logger(__name__)

celery_app = Celery(
    "adversaria",
    broker=_settings.celery_broker_url,
    backend=_settings.celery_result_backend,
    include=["adversaria.workers.celery_app"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,      # One task at a time (gen is slow)
    task_time_limit=600,               # 10-min hard limit per task
    task_soft_time_limit=540,
    result_expires=3600,
)


# ─── Task: run full design pipeline ──────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="adversaria.run_pipeline",
    max_retries=2,
    default_retry_delay=30,
)
def run_pipeline_task(self, job_id: str, state_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Runs the full LangGraph design pipeline asynchronously.
    Called by FastAPI after validating the brief request.
    Updates job status in Postgres at each major step via Redis pub/sub.
    """
    return asyncio.get_event_loop().run_until_complete(
        _run_pipeline_async(self, job_id, state_dict)
    )


async def _run_pipeline_async(task, job_id: str, state_dict: dict[str, Any]) -> dict[str, Any]:
    from adversaria.schemas import DesignState  # noqa: PLC0415
    from adversaria.agents.graph import create_compiled_graph  # noqa: PLC0415
    from adversaria.db.session import AsyncSessionLocal  # noqa: PLC0415
    from adversaria.db.models import DesignJob  # noqa: PLC0415
    from sqlalchemy import select  # noqa: PLC0415
    import redis.asyncio as aioredis  # noqa: PLC0415

    redis_client = aioredis.from_url(_settings.redis_url)

    async def publish_progress(agent: str, pct: float, extra: dict | None = None) -> None:
        """Publish real-time progress to Redis pub/sub channel."""
        payload = json.dumps({"job_id": job_id, "agent": agent, "pct": pct, **(extra or {})})
        await redis_client.publish(f"job:{job_id}", payload)

    try:
        await publish_progress("system", 0.05, {"status": "starting"})

        # Build initial state
        state = DesignState(**state_dict)

        # Compile graph (no checkpointer for Celery — state is in Redis/Postgres)
        app = await create_compiled_graph()

        config = {"configurable": {"thread_id": job_id}}

        final_state: DesignState | None = None

        # Stream events for progress tracking
        async for event in app.astream_events(state, config=config, version="v2"):
            kind = event.get("event", "")
            node = event.get("name", "")

            if kind == "on_chain_start":
                pct_map = {
                    "retrieve_brand_context": 0.10,
                    "creative_director": 0.20,
                    "senior_designer": 0.35,
                    "generate_image": 0.50,
                    "critique_panel": 0.65,
                    "eval_harness": 0.80,
                    "build_rationale": 0.90,
                }
                pct = pct_map.get(node, 0.5)
                await publish_progress(node, pct)

            if kind == "on_chain_end" and node == "build_rationale":
                output = event.get("data", {}).get("output", {})
                if output:
                    final_state = DesignState(**{**state_dict, **output})

        # Persist final state to Postgres
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(DesignJob).where(DesignJob.id == job_id))
            job = result.scalar_one_or_none()
            if job and final_state:
                job.status = final_state.status.value
                job.creative_strategy = final_state.creative_strategy
                job.spawned_agents = final_state.spawned_agents
                job.layout_spec = final_state.layout_spec
                job.critique_log = final_state.critique_log[-1] if final_state.critique_log else None
                job.rationale = final_state.rationale
                job.eval_scores = final_state.eval_scores
                job.generated_image_url = final_state.generated_image_url
                await session.commit()

        await publish_progress("system", 1.0, {"status": "complete"})
        await redis_client.aclose()

        return {"job_id": job_id, "status": "complete"}

    except Exception as exc:
        logger.exception("Pipeline failed for job %s", job_id)
        await publish_progress("system", -1, {"status": "error", "error": str(exc)})
        await redis_client.aclose()

        # Update job status in DB
        from adversaria.db.session import AsyncSessionLocal as Session  # noqa: PLC0415
        from adversaria.db.models import DesignJob as DJ  # noqa: PLC0415
        from sqlalchemy import select as sel  # noqa: PLC0415
        async with Session() as session:
            result = await session.execute(sel(DJ).where(DJ.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.status = "failed"
                job.error_message = str(exc)
                await session.commit()

        raise task.retry(exc=exc, countdown=30) from exc


# ─── Task: brand ingestion ────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="adversaria.ingest_brand_assets",
    max_retries=3,
    default_retry_delay=10,
)
def ingest_brand_assets_task(
    self, brand_id: str, s3_keys: list[str]
) -> dict[str, Any]:
    return asyncio.get_event_loop().run_until_complete(
        _ingest_assets_async(brand_id, s3_keys)
    )


async def _ingest_assets_async(brand_id: str, s3_keys: list[str]) -> dict[str, Any]:
    """
    Downloads assets from S3, runs preprocessing LLM pass to chunk brand
    guidelines into semantic rule units, then upserts into Qdrant.
    """
    from adversaria.services.ingestion import ingest_brand_assets  # noqa: PLC0415
    result = await ingest_brand_assets(brand_id, s3_keys)
    return result
