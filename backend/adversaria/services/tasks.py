"""
adversaria/services/tasks.py — Unified background task dispatcher.

Routes tasks to Celery or executes them in-process using asyncio.create_task.
Enables running the full agentic pipeline on Render free tier without Celery/Redis background processes.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any

from adversaria.config import get_settings

_settings = get_settings()


def dispatch_run_pipeline(job_id: str, state_dict: dict[str, Any]) -> str:
    """Dispatches the full design pipeline task."""
    if _settings.celery_enabled:
        from adversaria.workers.celery_app import run_pipeline_task
        run_pipeline_task.apply_async(args=[job_id, state_dict], task_id=job_id)
    else:
        from adversaria.workers.celery_app import _run_pipeline_async
        # Spawn as a background task on the current running event loop
        asyncio.create_task(_run_pipeline_async(task=None, job_id=job_id, state_dict=state_dict))
    return job_id


def dispatch_ingest_brand_assets(brand_id: str, s3_keys: list[str]) -> str:
    """Dispatches the brand asset ingestion task."""
    task_id = str(uuid.uuid4())
    if _settings.celery_enabled:
        from adversaria.workers.celery_app import ingest_brand_assets_task
        ingest_brand_assets_task.apply_async(args=[brand_id, s3_keys], task_id=task_id)
    else:
        from adversaria.workers.celery_app import _ingest_assets_async
        asyncio.create_task(_ingest_assets_async(brand_id=brand_id, s3_keys=s3_keys))
    return task_id


def dispatch_run_inpaint(
    task_id: str,
    gen_task_dict: dict[str, Any],
    image_url: str,
    mask_url: str,
) -> str:
    """Dispatches the localized image inpainting task."""
    if _settings.celery_enabled:
        from adversaria.workers.celery_app import run_inpaint_task
        run_inpaint_task.apply_async(
            args=[task_id, gen_task_dict, image_url, mask_url],
            task_id=task_id,
        )
    else:
        from adversaria.workers.celery_app import _run_inpaint_async
        asyncio.create_task(
            _run_inpaint_async(
                task=None,
                task_id=task_id,
                gen_task_dict=gen_task_dict,
                image_url=image_url,
                mask_url=mask_url,
            )
        )
    return task_id
