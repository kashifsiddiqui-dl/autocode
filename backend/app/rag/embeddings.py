"""OpenAI embedding service with batch processing and retry logic."""

from __future__ import annotations

import asyncio
import logging
from itertools import islice
from typing import Sequence

from openai import AsyncOpenAI, APIError, RateLimitError

logger = logging.getLogger(__name__)

_MAX_BATCH = 2048
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0


class EmbeddingService:
    """Generates embeddings via the OpenAI API with batching and retry."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-large",
        dimensions: int = 1024,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._dimensions = dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts, automatically batching if > MAX_BATCH."""
        if not texts:
            return []

        batches = list(_chunked(texts, _MAX_BATCH))
        all_embeddings: list[list[float]] = []

        for batch in batches:
            embeddings = await self._embed_with_retry(batch)
            all_embeddings.extend(embeddings)

        return all_embeddings

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
        results = await self._embed_with_retry([text])
        return results[0]

    async def _embed_with_retry(self, texts: list[str]) -> list[list[float]]:
        last_exc: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                response = await self._client.embeddings.create(
                    input=texts,
                    model=self._model,
                    dimensions=self._dimensions,
                )
                sorted_data = sorted(response.data, key=lambda d: d.index)
                return [d.embedding for d in sorted_data]

            except RateLimitError as exc:
                last_exc = exc
                delay = _RETRY_BASE_DELAY * (2**attempt)
                logger.warning(
                    "Rate limited on embedding attempt %d/%d, retrying in %.1fs",
                    attempt + 1,
                    _MAX_RETRIES,
                    delay,
                )
                await asyncio.sleep(delay)

            except APIError as exc:
                last_exc = exc
                if exc.status_code and exc.status_code >= 500:
                    delay = _RETRY_BASE_DELAY * (2**attempt)
                    logger.warning(
                        "Server error on embedding attempt %d/%d (status %s), retrying in %.1fs",
                        attempt + 1,
                        _MAX_RETRIES,
                        exc.status_code,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise

        raise RuntimeError(
            f"Embedding failed after {_MAX_RETRIES} retries"
        ) from last_exc


def _chunked(iterable: Sequence, size: int):
    it = iter(iterable)
    while True:
        batch = list(islice(it, size))
        if not batch:
            break
        yield batch
