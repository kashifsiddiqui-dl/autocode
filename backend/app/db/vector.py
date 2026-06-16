"""Qdrant vector database client wrapper."""

from __future__ import annotations

import logging
from typing import ClassVar

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import settings

logger = logging.getLogger(__name__)

# Collection name constants
ICD10CM_CODES_COLLECTION = "icd10cm_codes"
ICD10CM_INDEX_COLLECTION = "icd10cm_index"


class QdrantManager:
    """Manages the Qdrant client lifecycle and collection initialization."""

    _COLLECTIONS: ClassVar[dict[str, int]] = {
        ICD10CM_CODES_COLLECTION: settings.EMBEDDING_DIMENSIONS,
        ICD10CM_INDEX_COLLECTION: settings.EMBEDDING_DIMENSIONS,
    }

    def __init__(self) -> None:
        self._client: AsyncQdrantClient | None = None

    async def connect(self) -> None:
        """Create the async Qdrant client."""
        self._client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            timeout=30,
        )
        logger.info("Connected to Qdrant at %s", settings.QDRANT_URL)

    async def close(self) -> None:
        """Close the Qdrant client."""
        if self._client is not None:
            await self._client.close()
            self._client = None
            logger.info("Qdrant client closed")

    def get_client(self) -> AsyncQdrantClient:
        """Return the active client, raising if not connected."""
        if self._client is None:
            raise RuntimeError("QdrantManager is not connected — call connect() first")
        return self._client

    async def init_collections(self) -> None:
        """Create collections if they don't already exist."""
        client = self.get_client()
        existing = {c.name for c in (await client.get_collections()).collections}

        for name, dim in self._COLLECTIONS.items():
            if name not in existing:
                await client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
                )
                logger.info("Created Qdrant collection: %s (dim=%d)", name, dim)
            else:
                logger.info("Qdrant collection already exists: %s", name)


qdrant_manager = QdrantManager()
