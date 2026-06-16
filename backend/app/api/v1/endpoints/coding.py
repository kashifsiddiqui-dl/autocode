"""Coding analysis endpoints — the core medical coding API."""

from __future__ import annotations

import json
import logging
import math
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from app.core.dependencies import (
    AuthUser,
    DBSession,
    get_reranker,
    get_retriever,
)
from app.core.exceptions import NotFoundError
from app.rag.reranker import CrossEncoderReranker
from app.rag.retriever import HybridRetriever
from app.schemas.coding import (
    CodingRequest,
    CodingResultResponse,
    CodingSessionResponse,
    CodingSessionSummary,
    FeedbackRequest,
)
from app.schemas.common import PaginatedResponse
from app.schemas.session import SessionFeedback
from app.services.audit_service import AuditService
from app.services.coding_service import CodingService

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_coding_service(
    retriever: HybridRetriever = Depends(get_retriever),
    reranker: CrossEncoderReranker = Depends(get_reranker),
) -> CodingService:
    return CodingService(retriever=retriever, reranker=reranker)


@router.post("/analyze", response_model=CodingSessionResponse)
async def analyze(
    body: CodingRequest,
    request: Request,
    user: AuthUser,
    db: DBSession,
    coding_svc: CodingService = Depends(_get_coding_service),
):
    """Run the RAG coding pipeline on clinical text.

    Supports SSE streaming when Accept: text/event-stream is sent.
    """
    accept = request.headers.get("accept", "")
    if "text/event-stream" in accept:
        return await _analyze_stream(body, request, user, db, coding_svc)

    session = await coding_svc.create_session(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        clinical_text=body.clinical_text,
        patient_id=body.patient_id,
        standard_code=body.options.standard,
        llm_provider=body.options.llm_provider,
        llm_model=body.options.llm_model,
        options={
            "billable_only": body.options.billable_only,
            "chapter_filter": body.options.chapter_filter,
            "max_results": body.options.max_results,
            "min_confidence": body.options.min_confidence,
        },
    )

    audit = AuditService(db)
    await audit.log_action(
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="coding_session.created",
        resource_type="CodingSession",
        resource_id=str(session.id),
        details={
            "llm_provider": session.llm_provider,
            "llm_model": session.llm_model,
            "result_count": len(session.results) if session.results else 0,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return CodingSessionResponse.model_validate(session)


async def _analyze_stream(
    body: CodingRequest,
    request: Request,
    user: AuthUser,
    db: DBSession,
    coding_svc: CodingService,
) -> EventSourceResponse:
    async def event_generator():
        async for event in coding_svc.create_session_stream(
            db,
            tenant_id=user.tenant_id,
            user_id=user.id,
            clinical_text=body.clinical_text,
            patient_id=body.patient_id,
            standard_code=body.options.standard,
            llm_provider=body.options.llm_provider,
            llm_model=body.options.llm_model,
            options={
                "billable_only": body.options.billable_only,
                "chapter_filter": body.options.chapter_filter,
                "max_results": body.options.max_results,
                "min_confidence": body.options.min_confidence,
            },
        ):
            yield {
                "event": event.get("event", "message"),
                "data": json.dumps(event.get("data", {})),
            }

    return EventSourceResponse(event_generator())


@router.get("/sessions", response_model=PaginatedResponse[CodingSessionSummary])
async def list_sessions(
    user: AuthUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    coding_svc: CodingService = Depends(_get_coding_service),
):
    """List the authenticated user's coding sessions."""
    user_id = user.id if user.role != "admin" else None
    sessions, total = await coding_svc.list_sessions(
        db, tenant_id=user.tenant_id, user_id=user_id, page=page, size=size,
    )

    summaries = []
    for s in sessions:
        summaries.append(
            CodingSessionSummary(
                id=s.id,
                patient_id=s.patient_id,
                status=s.status,
                llm_provider=s.llm_provider,
                llm_model=s.llm_model,
                created_at=s.created_at,
                completed_at=s.completed_at,
                result_count=len(s.results) if s.results else 0,
            )
        )

    return PaginatedResponse(
        items=summaries,
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size else 0,
    )


@router.get("/sessions/{session_id}", response_model=CodingSessionResponse)
async def get_session(
    session_id: uuid.UUID,
    user: AuthUser,
    db: DBSession,
    coding_svc: CodingService = Depends(_get_coding_service),
):
    """Get a coding session with its results."""
    session = await coding_svc.get_session(db, session_id, user.tenant_id)
    if session is None:
        raise NotFoundError(f"Session {session_id} not found")
    return CodingSessionResponse.model_validate(session)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    user: AuthUser,
    db: DBSession,
    coding_svc: CodingService = Depends(_get_coding_service),
):
    """Soft delete a coding session."""
    deleted = await coding_svc.delete_session(db, session_id, user.tenant_id)
    if not deleted:
        raise NotFoundError(f"Session {session_id} not found")


@router.post("/sessions/{session_id}/feedback")
async def submit_feedback(
    session_id: uuid.UUID,
    body: SessionFeedback,
    user: AuthUser,
    db: DBSession,
    request: Request,
    coding_svc: CodingService = Depends(_get_coding_service),
):
    """Submit feedback on a coding result."""
    result = await coding_svc.submit_feedback(
        db,
        session_id=session_id,
        tenant_id=user.tenant_id,
        result_id=body.code_result_id,
        is_correct=body.is_correct,
        correction=body.correction,
    )
    if result is None:
        raise NotFoundError("Session or result not found")

    audit = AuditService(db)
    await audit.log_action(
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="coding_result.feedback",
        resource_type="CodingResult",
        resource_id=str(body.code_result_id),
        details={
            "session_id": str(session_id),
            "is_correct": body.is_correct,
            "correction": body.correction,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return CodingResultResponse.model_validate(result)
