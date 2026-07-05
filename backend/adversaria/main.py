"""
adversaria/main.py — FastAPI application entrypoint.
"""
from __future__ import annotations

import structlog
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adversaria.config import get_settings
from adversaria.api.routes import router
from adversaria.db.session import create_tables
from adversaria.services.vector_store import get_vector_store

_settings = get_settings()
log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle."""
    log.info("adversaria.startup", env=_settings.app_env)

    # Create DB tables (dev only; use Alembic in production)
    if _settings.app_env == "development":
        await create_tables()

    # Bootstrap Qdrant collections
    vs = get_vector_store()
    await vs.ensure_collections()

    log.info("adversaria.ready")
    yield

    log.info("adversaria.shutdown")


app = FastAPI(
    title="Adversaria AI — Backend API",
    description="Adversarial Multi-Agent Creative Intelligence Engine",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "env": _settings.app_env}
