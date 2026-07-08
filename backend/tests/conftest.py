"""tests/conftest.py — shared fixtures and environment setup."""
from __future__ import annotations
import os
import pytest

# Prevent any real API calls from test env
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-placeholder")
os.environ.setdefault("VOYAGE_API_KEY", "")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-prod")
