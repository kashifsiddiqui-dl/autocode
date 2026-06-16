"""Patient CRUD endpoints."""

from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, Query, status

from app.core.dependencies import AuthUser, DBSession, require_role
from app.core.exceptions import NotFoundError
from app.schemas.coding import CodingSessionSummary
from app.schemas.common import PaginatedResponse
from app.schemas.patient import PatientCreate, PatientList, PatientResponse, PatientUpdate
from app.services.coding_service import CodingService
from app.services.patient_service import PatientService

router = APIRouter()


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    body: PatientCreate,
    user: AuthUser,
    db: DBSession,
):
    """Create a new patient record."""
    svc = PatientService(db)
    patient = await svc.create(tenant_id=user.tenant_id, user_id=user.id, data=body)
    return PatientResponse.model_validate(patient)


@router.get("", response_model=PaginatedResponse[PatientList])
async def list_patients(
    user: AuthUser,
    db: DBSession,
    search: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    """List patients with optional name/MRN search."""
    svc = PatientService(db)
    patients, total = await svc.list(
        user.tenant_id, search=search, page=page, size=size,
    )
    return PaginatedResponse(
        items=[PatientList.model_validate(p) for p in patients],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size else 0,
    )


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: uuid.UUID,
    user: AuthUser,
    db: DBSession,
):
    """Get a single patient by ID."""
    svc = PatientService(db)
    patient = await svc.get(patient_id, user.tenant_id)
    if patient is None:
        raise NotFoundError(f"Patient {patient_id} not found")
    return PatientResponse.model_validate(patient)


@router.patch("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: uuid.UUID,
    body: PatientUpdate,
    user: AuthUser,
    db: DBSession,
):
    """Update an existing patient."""
    svc = PatientService(db)
    patient = await svc.update(patient_id, user.tenant_id, body)
    if patient is None:
        raise NotFoundError(f"Patient {patient_id} not found")
    return PatientResponse.model_validate(patient)


@router.get("/{patient_id}/sessions", response_model=PaginatedResponse[CodingSessionSummary])
async def list_patient_sessions(
    patient_id: uuid.UUID,
    user: AuthUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    """List coding sessions for a specific patient."""
    from sqlalchemy import func, select

    from app.models.coding_session import CodingSession

    base = (
        select(CodingSession)
        .where(
            CodingSession.tenant_id == user.tenant_id,
            CodingSession.patient_id == patient_id,
        )
    )

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * size
    rows = (
        base.order_by(CodingSession.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    result = await db.execute(rows)
    sessions = result.scalars().all()

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
