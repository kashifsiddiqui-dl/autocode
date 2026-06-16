"""Hybrid retriever: dense vector search on Qdrant with metadata filtering."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    Range,
    SearchParams,
)

from app.rag.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    chunk_id: str
    code: str
    description: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    chunk_text: str = ""


class HybridRetriever:
    """Stage 1+2 of the RAG pipeline: dense vector search plus metadata filtering."""

    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
        embedding_service: EmbeddingService,
        collection_name: str = "icd10cm_codes",
    ) -> None:
        self._client = qdrant_client
        self._embedding = embedding_service
        self._collection = collection_name

    async def retrieve(
        self,
        query: str,
        top_k: int = 50,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        """Run dense vector search and apply metadata filters.

        Stage 1: Dense search on the "description" named vector with top_k * 2 candidates.
        Stage 2: Apply metadata filters (is_billable, chapter_num, etc.) and deduplicate.
        Returns up to top_k results sorted by score.
        """
        query_vector = await self._embedding.embed_query(query)

        qdrant_filter = self._build_filter(filters) if filters else None

        search_limit = top_k * 2

        try:
            hits = await self._client.search(
                collection_name=self._collection,
                query_vector=("description", query_vector),
                query_filter=qdrant_filter,
                limit=search_limit,
                with_payload=True,
                search_params=SearchParams(hnsw_ef=128, exact=False),
            )
        except Exception:
            logger.exception("Qdrant search failed, falling back to unnamed vector")
            hits = await self._client.search(
                collection_name=self._collection,
                query_vector=query_vector,
                query_filter=qdrant_filter,
                limit=search_limit,
                with_payload=True,
            )

        seen_codes: set[str] = set()
        results: list[RetrievalResult] = []

        for hit in hits:
            payload = hit.payload or {}
            code = payload.get("code", "")

            if code in seen_codes:
                continue
            seen_codes.add(code)

            if filters:
                if not self._passes_post_filter(payload, filters):
                    continue

            results.append(
                RetrievalResult(
                    chunk_id=str(hit.id),
                    code=code,
                    description=payload.get("description", ""),
                    score=hit.score,
                    metadata={
                        k: v
                        for k, v in payload.items()
                        if k not in ("description", "chunk_text")
                    },
                    chunk_text=payload.get("chunk_text", payload.get("description", "")),
                )
            )

            if len(results) >= top_k:
                break

        logger.info(
            "Retrieved %d results from %d candidates for query (%.60s...)",
            len(results),
            len(hits),
            query,
        )
        return results

    def _build_filter(self, filters: dict[str, Any]) -> Filter:
        conditions = []

        if "is_billable" in filters:
            conditions.append(
                FieldCondition(key="is_billable", match=MatchValue(value=filters["is_billable"]))
            )

        if "chapter_num" in filters:
            chapter = filters["chapter_num"]
            if isinstance(chapter, list):
                for ch in chapter:
                    conditions.append(
                        FieldCondition(key="chapter_num", match=MatchValue(value=ch))
                    )
            else:
                conditions.append(
                    FieldCondition(key="chapter_num", match=MatchValue(value=chapter))
                )

        if "chunk_type" in filters:
            conditions.append(
                FieldCondition(key="chunk_type", match=MatchValue(value=filters["chunk_type"]))
            )

        if "version_year" in filters:
            conditions.append(
                FieldCondition(
                    key="version_year", match=MatchValue(value=filters["version_year"])
                )
            )

        return Filter(must=conditions) if conditions else Filter()

    @staticmethod
    def _passes_post_filter(payload: dict[str, Any], filters: dict[str, Any]) -> bool:
        if "is_billable" in filters and payload.get("is_billable") != filters["is_billable"]:
            return False
        if "chapter_num" in filters:
            chapter = filters["chapter_num"]
            payload_chapter = payload.get("chapter_num")
            if isinstance(chapter, list):
                if payload_chapter not in chapter:
                    return False
            elif payload_chapter != chapter:
                return False
        return True
