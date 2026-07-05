"""
adversaria/config.py — Central settings (Pydantic v2 BaseSettings).
All values are read from environment variables / .env file.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    app_secret_key: str = "change-me"
    log_level: str = "INFO"

    # ── Anthropic / Claude ────────────────────────────────────────────────────
    anthropic_api_key: str
    anthropic_model: str = "claude-opus-4-5"
    director_model: str = "claude-opus-4-5"
    designer_model: str = "claude-sonnet-4-5"
    critic_model: str = "claude-haiku-4-5"

    # ── LangSmith ─────────────────────────────────────────────────────────────
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "adversaria-ai"
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # ── Voyage AI ─────────────────────────────────────────────────────────────
    voyage_api_key: str = ""
    voyage_model: str = "voyage-3"

    # ── OpenAI (fallback) ─────────────────────────────────────────────────────
    openai_api_key: str = ""

    # ── Qdrant ───────────────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_brand_rules_collection: str = "brand_rules"
    qdrant_moodboards_collection: str = "moodboards"

    # ── Postgres ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://adversaria:adversaria@localhost:5432/adversaria_db"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── S3 / MinIO ────────────────────────────────────────────────────────────
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket_name: str = "adversaria-assets"
    s3_region: str = "us-east-1"

    # ── Image Generation ──────────────────────────────────────────────────────
    replicate_api_token: str = ""
    fal_key: str = ""
    firefly_client_id: str = ""
    firefly_client_secret: str = ""
    comfyui_url: str = "http://localhost:8188"
    comfyui_workflow_dir: str = "comfyui_workflows"

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [s.strip() for s in v.split(",")]
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
