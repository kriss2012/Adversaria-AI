"""
adversaria/services/embeddings.py — Embedding service.

Priority:
  1. Voyage AI voyage-3 (primary, best for brand/marketing text)
  2. OpenAI text-embedding-3-large (fallback)
  3. CLIP for image embeddings
"""
from __future__ import annotations

import asyncio
import base64
import io
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
import numpy as np

from adversaria.config import get_settings

_settings = get_settings()


class EmbeddingService:
    """Unified embedding service — text via Voyage AI, images via CLIP."""

    def __init__(self) -> None:
        self._voyage_client: Any = None
        self._openai_client: Any = None

    # ── Text Embeddings ───────────────────────────────────────────────────────

    async def embed_texts(
        self,
        texts: list[str],
        input_type: str = "document",  # "document" | "query"
    ) -> list[list[float]]:
        """
        Embed a batch of text strings.
        Falls back to OpenAI if Voyage is unavailable.
        """
        if _settings.voyage_api_key:
            return await self._voyage_embed(texts, input_type)
        elif _settings.openai_api_key:
            return await self._openai_embed(texts)
        else:
            # Deterministic mock for development (no keys needed)
            return [self._mock_embedding(t) for t in texts]

    async def embed_query(self, query: str) -> list[float]:
        results = await self.embed_texts([query], input_type="query")
        return results[0]

    async def _voyage_embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        import voyageai  # noqa: PLC0415
        client = voyageai.AsyncClient(api_key=_settings.voyage_api_key)
        result = await client.embed(
            texts=texts,
            model=_settings.voyage_model,
            input_type=input_type,
        )
        return result.embeddings  # type: ignore[return-value]

    async def _openai_embed(self, texts: list[str]) -> list[list[float]]:
        from openai import AsyncOpenAI  # noqa: PLC0415
        client = AsyncOpenAI(api_key=_settings.openai_api_key)
        response = await client.embeddings.create(
            model="text-embedding-3-large",
            input=texts,
        )
        return [r.embedding for r in response.data]

    def _mock_embedding(self, text: str, dim: int = 1024) -> list[float]:
        """
        Deterministic mock embedding based on text hash.
        Useful for dev without API keys.
        """
        rng = np.random.default_rng(hash(text) % (2**32))
        vec = rng.standard_normal(dim).astype(np.float32)
        vec = vec / (np.linalg.norm(vec) + 1e-8)
        return vec.tolist()

    # ── Image Embeddings (CLIP) ───────────────────────────────────────────────

    async def embed_image_file(self, image_path: Path) -> list[float]:
        """
        Generate CLIP embedding for an image file.
        Uses transformers CLIP locally (no external API needed).
        """
        return await asyncio.get_event_loop().run_in_executor(
            None, self._clip_embed_sync, image_path
        )

    def _clip_embed_sync(self, image_path: Path) -> list[float]:
        try:
            from PIL import Image  # noqa: PLC0415
            from transformers import CLIPModel, CLIPProcessor  # noqa: PLC0415
            import torch  # noqa: PLC0415

            model_name = "openai/clip-vit-base-patch32"
            processor = CLIPProcessor.from_pretrained(model_name)
            model = CLIPModel.from_pretrained(model_name)
            model.eval()

            image = Image.open(image_path).convert("RGB")
            inputs = processor(images=image, return_tensors="pt")
            with torch.no_grad():
                features = model.get_image_features(**inputs)
                features = features / features.norm(dim=-1, keepdim=True)
            return features[0].tolist()
        except ImportError:
            # Fallback: deterministic mock
            return self._mock_embedding(str(image_path), dim=768)

    # ── Taste Vector Update ───────────────────────────────────────────────────

    @staticmethod
    def update_taste_vector(
        taste_vector: list[float],
        new_signal: list[float],
        reward: float,
        lr: float = 0.05,
    ) -> list[float]:
        """
        Incremental taste vector update (online learning).
        reward in [-1, +1]: +1 = strongly approved, -1 = strongly rejected.
        Uses a signed gradient step toward/away from the concept embedding.
        """
        tv = np.array(taste_vector, dtype=np.float32)
        sig = np.array(new_signal, dtype=np.float32)

        # Signed update: move taste vector toward approved concepts
        delta = reward * lr * (sig - tv)
        updated = tv + delta

        # Re-normalize to unit sphere
        norm = np.linalg.norm(updated)
        if norm > 0:
            updated = updated / norm

        return updated.tolist()

    @staticmethod
    def init_taste_vector(dim: int = 1024) -> list[float]:
        """Initialize a zero taste vector (will be shaped by first signal)."""
        return [0.0] * dim

    @staticmethod
    def rerank_by_taste(
        concepts: list[dict[str, Any]],
        taste_vector: list[float],
        embedding_key: str = "embedding",
    ) -> list[dict[str, Any]]:
        """
        Re-rank a list of concepts by cosine similarity to the taste vector.
        Concepts with embeddings closer to the brand's taste profile rank higher.
        """
        if not taste_vector or all(v == 0 for v in taste_vector):
            return concepts  # No taste signal yet — return as-is

        tv = np.array(taste_vector, dtype=np.float32)

        def taste_score(concept: dict[str, Any]) -> float:
            if embedding_key not in concept:
                return 0.0
            emb = np.array(concept[embedding_key], dtype=np.float32)
            return float(np.dot(emb, tv) / (np.linalg.norm(emb) * np.linalg.norm(tv) + 1e-8))

        return sorted(concepts, key=taste_score, reverse=True)


# ── Singleton ──────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
