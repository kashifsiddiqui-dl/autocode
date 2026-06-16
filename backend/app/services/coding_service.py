"""Coding service — orchestrates the RAG pipeline for medical code suggestions."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.coding_result import CodingResult
from app.models.coding_session import CodingSession
from app.models.coding_standard import CodingStandard
from app.rag.llm.factory import LLMFactory
from app.rag.pipeline import RAGPipeline
from app.rag.reranker import CrossEncoderReranker
from app.rag.retriever import HybridRetriever

logger = logging.getLogger(__name__)


class CodingService:
    """Orchestrates clinical text -> ICD code suggestions via RAG."""

    def __init__(
        self,
        retriever: HybridRetriever,
        reranker: CrossEncoderReranker,
    ) -> None:
        self._retriever = retriever
        self._reranker = reranker

    async def create_session(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        clinical_text: str,
        patient_id: uuid.UUID | None = None,
        standard_code: str = "icd10cm",
        llm_provider: str | None = None,
        llm_model: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> CodingSession:
        """Create a coding session and run the full RAG pipeline."""
        provider_name = llm_provider or settings.LLM_PROVIDER
        model_name = llm_model or settings.LLM_MODEL
        api_key = (
            settings.ANTHROPIC_API_KEY
            if provider_name == "anthropic"
            else settings.OPENAI_API_KEY
        )
        llm = LLMFactory.create(provider=provider_name, api_key=api_key, model=model_name)

        std_result = await db.execute(
            select(CodingStandard).where(CodingStandard.code == standard_code)
        )
        standard = std_result.scalar_one_or_none()
        if standard is None:
            raise ValueError(f"Unknown coding standard: {standard_code}")

        session = CodingSession(
            tenant_id=tenant_id,
            user_id=user_id,
            patient_id=patient_id,
            standard_id=standard.id,
            clinical_input=clinical_text,
            llm_provider=provider_name,
            llm_model=model_name,
            status="processing",
        )
        db.add(session)
        await db.flush()

        pipeline = RAGPipeline(
            retriever=self._retriever,
            reranker=self._reranker,
            llm_provider=llm,
            db_session=db,
        )

        try:
            output = await pipeline.process_clinical_notes(
                clinical_text=clinical_text,
                standard_code=standard_code,
                options=options,
            )

            for i, code_result in enumerate(output.codes):
                cr = CodingResult(
                    session_id=session.id,
                    icd_code=code_result.code,
                    icd_description=code_result.description,
                    confidence_score=code_result.confidence_score,
                    rationale=code_result.rationale,
                    coding_instructions=code_result.coding_instructions,
                    seventh_char=code_result.seventh_char,
                    is_validated=code_result.is_validated,
                    is_primary=(i == 0),
                    sequence_order=i,
                )
                db.add(cr)

            session.status = "completed"
            session.completed_at = datetime.now(timezone.utc)
            session.rag_metadata = output.session_metadata

        except Exception:
            session.status = "error"
            logger.exception("RAG pipeline failed for session %s", session.id)
            raise
        finally:
            await db.flush()

        return session

    async def create_session_stream(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        clinical_text: str,
        patient_id: uuid.UUID | None = None,
        standard_code: str = "icd10cm",
        llm_provider: str | None = None,
        llm_model: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Run the pipeline with streaming SSE events."""
        provider_name = llm_provider or settings.LLM_PROVIDER
        model_name = llm_model or settings.LLM_MODEL
        api_key = (
            settings.ANTHROPIC_API_KEY
            if provider_name == "anthropic"
            else settings.OPENAI_API_KEY
        )
        llm = LLMFactory.create(provider=provider_name, api_key=api_key, model=model_name)

        std_result = await db.execute(
            select(CodingStandard).where(CodingStandard.code == standard_code)
        )
        standard = std_result.scalar_one_or_none()
        if standard is None:
            raise ValueError(f"Unknown coding standard: {standard_code}")

        session = CodingSession(
            tenant_id=tenant_id,
            user_id=user_id,
            patient_id=patient_id,
            standard_id=standard.id,
            clinical_input=clinical_text,
            llm_provider=provider_name,
            llm_model=model_name,
            status="processing",
        )
        db.add(session)
        await db.flush()

        yield {"event": "session", "data": {"session_id": str(session.id), "status": "processing"}}

        pipeline = RAGPipeline(
            retriever=self._retriever,
            reranker=self._reranker,
            llm_provider=llm,
            db_session=db,
        )

        code_results: list[dict[str, Any]] = []
        async for event in pipeline.process_clinical_notes_stream(
            clinical_text=clinical_text,
            standard_code=standard_code,
            options=options,
        ):
            if event.get("event") == "code":
                code_results.append(event["data"])
            yield event

        for i, code_data in enumerate(code_results):
            cr = CodingResult(
                session_id=session.id,
                icd_code=code_data["code"],
                icd_description=code_data["description"],
                confidence_score=code_data.get("confidence_score", 0.5),
                rationale=code_data.get("rationale"),
                is_validated=code_data.get("is_validated", False),
                is_primary=(i == 0),
                sequence_order=i,
            )
            db.add(cr)

        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)
        await db.flush()

    async def get_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> CodingSession | None:
        stmt = select(CodingSession).where(
            CodingSession.id == session_id,
            CodingSession.tenant_id == tenant_id,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[CodingSession], int]:
        base = select(CodingSession).where(CodingSession.tenant_id == tenant_id)

        if user_id is not None:
            base = base.where(CodingSession.user_id == user_id)
        if status is not None:
            base = base.where(CodingSession.status == status)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        offset = (page - 1) * size
        rows_stmt = base.order_by(CodingSession.created_at.desc()).offset(offset).limit(size)
        result = await db.execute(rows_stmt)
        sessions = list(result.scalars().all())

        return sessions, total

    async def delete_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        session = await self.get_session(db, session_id, tenant_id)
        if session is None:
            return False
        await db.delete(session)
        await db.flush()
        return True

    async def submit_feedback(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        tenant_id: uuid.UUID,
        result_id: uuid.UUID,
        is_correct: bool,
        correction: str | None = None,
    ) -> CodingResult | None:
        session = await self.get_session(db, session_id, tenant_id)
        if session is None:
            return None

        result = await db.execute(
            select(CodingResult).where(
                CodingResult.id == result_id,
                CodingResult.session_id == session_id,
            )
        )
        coding_result = result.scalar_one_or_none()
        if coding_result is None:
            return None

        coding_result.is_validated = is_correct
        if correction is not None:
            coding_result.icd_code = correction

        await db.flush()
        return coding_result
