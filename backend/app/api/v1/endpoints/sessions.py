"""Session management endpoints — extends coding.py with session-specific operations."""

from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.dependencies import AuthUser, DBSession
from app.core.exceptions import NotFoundError
from app.schemas.coding import CodingResultResponse, CodingSessionResponse, CodingSessionSummary
from app.schemas.common import PaginatedResponse
from app.schemas.session import SessionFeedback
from app.services.audit_service import AuditService
from app.services.session_service import SessionService

router = APIRouter()


@router.get("", response_model=PaginatedResponse[CodingSessionSummary])
async def list_sessions(
    user: AuthUser,
    db: DBSession,
    user_id: uuid.UUID | None = Query(default=None),
    session_status: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    """List coding sessions with optional filters."""
    svc = SessionService(db)

    filter_user_id = user_id if user.role == "admin" else user.id

    sessions, total = await svc.list_sessions(
        user.tenant_id,
        user_id=filter_user_id,
        status=session_status,
        page=page,
        size=size,
    )

    summaries = [
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
        for s in sessions
    ]

    return PaginatedResponse(
        items=summaries,
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size else 0,
    )


@router.get("/{session_id}", response_model=CodingSessionResponse)
async def get_session(
    session_id: uuid.UUID,
    user: AuthUser,
    db: DBSession,
):
    """Get a session with its results."""
    svc = SessionService(db)
    session = await svc.get_session(session_id, user.tenant_id)
    if session is None:
        raise NotFoundError(f"Session {session_id} not found")
    return CodingSessionResponse.model_validate(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    user: AuthUser,
    db: DBSession,
    request: Request,
):
    """Delete a coding session and its results."""
    svc = SessionService(db)
    deleted = await svc.delete_session(session_id, user.tenant_id)
    if not deleted:
        raise NotFoundError(f"Session {session_id} not found")

    audit = AuditService(db)
    await audit.log_action(
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="coding_session.deleted",
        resource_type="CodingSession",
        resource_id=str(session_id),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/{session_id}/feedback", response_model=CodingResultResponse)
async def submit_feedback(
    session_id: uuid.UUID,
    body: SessionFeedback,
    user: AuthUser,
    db: DBSession,
    request: Request,
):
    """Submit feedback on a specific coding result."""
    svc = SessionService(db)
    coding_result = await svc.submit_feedback(
        tenant_id=user.tenant_id,
        user_id=user.id,
        feedback=body,
    )
    if coding_result is None:
        raise NotFoundError("Coding result not found")

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

    return CodingResultResponse.model_validate(coding_result)
