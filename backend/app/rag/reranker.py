"""Cross-encoder reranker using sentence-transformers."""

from __future__ import annotations

import logging

from sentence_transformers import CrossEncoder

from app.rag.retriever import RetrievalResult

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Reranks retrieval results by scoring (query, document) pairs with a cross-encoder."""

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        batch_size: int = 16,
    ) -> None:
        self._model_name = model_name
        self._batch_size = batch_size
        self._model: CrossEncoder | None = None

    def _get_model(self) -> CrossEncoder:
        if self._model is None:
            logger.info("Loading cross-encoder model: %s", self._model_name)
            self._model = CrossEncoder(self._model_name)
        return self._model

    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int = 10,
    ) -> list[RetrievalResult]:
        """Score each (query, chunk_text) pair and return the top_k by cross-encoder score."""
        if not results:
            return []

        model = self._get_model()

        pairs = [(query, r.chunk_text or r.description) for r in results]

        scores = model.predict(pairs, batch_size=self._batch_size, show_progress_bar=False)

        scored = list(zip(results, scores))
        scored.sort(key=lambda x: x[1], reverse=True)

        reranked: list[RetrievalResult] = []
        for result, score in scored[:top_k]:
            reranked.append(
                RetrievalResult(
                    chunk_id=result.chunk_id,
                    code=result.code,
                    description=result.description,
                    score=float(score),
                    metadata=result.metadata,
                    chunk_text=result.chunk_text,
                )
            )

        logger.info(
            "Reranked %d results down to %d (top score=%.4f, bottom score=%.4f)",
            len(results),
            len(reranked),
            reranked[0].score if reranked else 0,
            reranked[-1].score if reranked else 0,
        )
        return reranked
