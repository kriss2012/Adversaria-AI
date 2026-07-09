"""
adversaria/services/vector_store.py — Qdrant wrapper.

Three separate logical stores:
  1. brand_rules     — text embeddings of semantic brand rule units
  2. moodboards      — image (CLIP/SigLIP) embeddings of visual references
  3. concept_history — text embeddings of past approved concepts (per brand)
                       used for novelty scoring
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import Distance, PointStruct, VectorParams

from adversaria.config import get_settings
from adversaria.schemas import BrandRule

_settings = get_settings()

BRAND_RULES_COLLECTION = _settings.qdrant_brand_rules_collection
MOODBOARDS_COLLECTION = _settings.qdrant_moodboards_collection
CONCEPT_HISTORY_COLLECTION = "concept_history"

# Dimension of voyage-3 text embeddings
TEXT_EMBEDDING_DIM = 1024
# CLIP image embedding dim (clip-vit-large-patch14)
IMAGE_EMBEDDING_DIM = 768


class VectorStore:
    """Async wrapper around Qdrant with collection lifecycle management."""

    def __init__(self) -> None:
        self._client: AsyncQdrantClient | None = None

    @property
    def client(self) -> AsyncQdrantClient:
        if self._client is None:
            self._client = AsyncQdrantClient(
                url=_settings.qdrant_url,
                api_key=_settings.qdrant_api_key or None,
            )
        return self._client

    # ── Collection bootstrap ─────────────────────────────────────────────────

    async def ensure_collections(self) -> None:
        """Idempotently create required Qdrant collections."""
        specs = [
            (BRAND_RULES_COLLECTION, TEXT_EMBEDDING_DIM, Distance.COSINE),
            (MOODBOARDS_COLLECTION, IMAGE_EMBEDDING_DIM, Distance.COSINE),
            (CONCEPT_HISTORY_COLLECTION, TEXT_EMBEDDING_DIM, Distance.COSINE),
        ]
        existing = {c.name for c in (await self.client.get_collections()).collections}
        for name, dim, distance in specs:
            if name not in existing:
                await self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=dim, distance=distance),
                )

    # ── Brand rules ──────────────────────────────────────────────────────────

    async def upsert_brand_rules(
        self,
        brand_id: str,
        rules: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> list[str]:
        """
        Upsert semantic brand rule units into Qdrant.
        Each rule must have: rule_type, rule_text, source_file.
        Returns list of upserted point IDs.
        """
        assert len(rules) == len(embeddings), "rules and embeddings must align"

        points = []
        ids = []
        for rule, emb in zip(rules, embeddings, strict=True):
            pid = str(uuid.uuid4())
            ids.append(pid)
            points.append(
                PointStruct(
                    id=pid,
                    vector=emb,
                    payload={
                        "brand_id": brand_id,
                        "rule_type": rule["rule_type"],
                        "rule_text": rule["rule_text"],
                        "source_file": rule["source_file"],
                    },
                )
            )

        await self.client.upsert(collection_name=BRAND_RULES_COLLECTION, points=points)
        return ids

    async def retrieve_brand_rules(
        self,
        brand_id: str,
        query_embedding: list[float],
        top_k: int = 10,
        rule_types: list[str] | None = None,
    ) -> list[BrandRule]:
        """
        Semantic + metadata-filtered retrieval of brand rules.
        If rule_types is provided, only those categories are searched.
        """
        filters: list[models.Condition] = [
            models.FieldCondition(
                key="brand_id",
                match=models.MatchValue(value=brand_id),
            )
        ]
        if rule_types:
            filters.append(
                models.FieldCondition(
                    key="rule_type",
                    match=models.MatchAny(any=rule_types),
                )
            )

        results = await self.client.search(
            collection_name=BRAND_RULES_COLLECTION,
            query_vector=query_embedding,
            query_filter=models.Filter(must=filters),
            limit=top_k,
            with_payload=True,
        )

        return [
            BrandRule(
                rule_id=str(r.id),
                rule_type=r.payload["rule_type"],  # type: ignore[index]
                rule_text=r.payload["rule_text"],   # type: ignore[index]
                source_file=r.payload["source_file"],  # type: ignore[index]
                confidence=r.score,
                embedding_distance=1.0 - r.score,
            )
            for r in results
        ]

    # ── Concept history (novelty scoring) ────────────────────────────────────

    async def upsert_concept_embedding(
        self,
        brand_id: str,
        concept_id: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store an approved concept embedding for future novelty comparisons."""
        await self.client.upsert(
            collection_name=CONCEPT_HISTORY_COLLECTION,
            points=[
                PointStruct(
                    id=concept_id,
                    vector=embedding,
                    payload={"brand_id": brand_id, **(metadata or {})},
                )
            ],
        )

    async def compute_novelty_score(
        self,
        brand_id: str,
        concept_embedding: list[float],
        top_k: int = 12,
    ) -> tuple[float, float]:
        """
        Returns (novelty_score 0-100, avg_cosine_distance 0-2).
        Higher distance from historical concepts = more novel.
        """
        results = await self.client.search(
            collection_name=CONCEPT_HISTORY_COLLECTION,
            query_vector=concept_embedding,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="brand_id", match=models.MatchValue(value=brand_id)
                    )
                ]
            ),
            limit=top_k,
            with_payload=False,
        )
        if not results:
            return 85.0, 1.7  # No history → highly novel by default

        avg_similarity = sum(r.score for r in results) / len(results)
        avg_distance = 1.0 - avg_similarity
        # Map distance [0, 2] → score [0, 100], with floor at 0.65 = 50pts
        novelty_score = min(100.0, max(0.0, (avg_distance / 1.5) * 100))
        return novelty_score, avg_distance

    async def compute_brand_fit_score(
        self,
        brand_id: str,
        concept_embedding: list[float],
    ) -> tuple[float, float]:
        """
        Computes brand fit as cosine similarity to the brand centroid
        (mean of all historical approved concept embeddings).
        Returns (brand_fit_score 0-100, centroid_cosine_similarity 0-1).
        """
        # Retrieve all approved concepts for this brand (no query filter on similarity)
        # Use scroll instead of search with a dummy query
        results, _ = await self.client.scroll(
            collection_name=CONCEPT_HISTORY_COLLECTION,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="brand_id", match=models.MatchValue(value=brand_id)
                    )
                ]
            ),
            with_vectors=True,
            limit=200,
        )
        if not results:
            return 70.0, 0.7  # Neutral when no history

        import numpy as np  # noqa: PLC0415
        vectors = np.array([p.vector for p in results if p.vector is not None])
        centroid = vectors.mean(axis=0)
        concept = np.array(concept_embedding)
        similarity = float(
            np.dot(concept, centroid) / (np.linalg.norm(concept) * np.linalg.norm(centroid) + 1e-8)
        )
        score = min(100.0, max(0.0, similarity * 100))
        return score, similarity

    # ── Moodboards (image embeddings) ────────────────────────────────────────

    async def upsert_moodboard(
        self,
        brand_id: str,
        asset_id: str,
        image_embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await self.client.upsert(
            collection_name=MOODBOARDS_COLLECTION,
            points=[
                PointStruct(
                    id=asset_id,
                    vector=image_embedding,
                    payload={"brand_id": brand_id, **(metadata or {})},
                )
            ],
        )

    async def find_similar_moodboards(
        self,
        brand_id: str,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Find moodboards visually similar to the query.

        Note: moodboards use IMAGE_EMBEDDING_DIM (768-dim CLIP).
        If a text query_embedding is passed (1024-dim voyage-3), we
        truncate + renormalise to 768-dim so dimensions align.
        This is a safe approximation for moodboard recall (not precision scoring).
        """
        import numpy as np  # noqa: PLC0415

        q = np.array(query_embedding, dtype=np.float32)
        if len(q) != IMAGE_EMBEDDING_DIM:
            q = q[:IMAGE_EMBEDDING_DIM]
            norm = np.linalg.norm(q)
            if norm > 0:
                q = q / norm

        results = await self.client.search(
            collection_name=MOODBOARDS_COLLECTION,
            query_vector=q.tolist(),
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="brand_id", match=models.MatchValue(value=brand_id)
                    )
                ]
            ),
            limit=top_k,
            with_payload=True,
        )
        return [{"id": str(r.id), "score": r.score, **r.payload} for r in results]  # type: ignore[misc]


# ── Singleton ─────────────────────────────────────────────────────────────────
_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
