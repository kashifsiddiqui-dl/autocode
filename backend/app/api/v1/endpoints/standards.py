"""Coding standards endpoints — list and inspect supported classification systems."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.core.dependencies import AuthUser, DBSession
from app.core.exceptions import NotFoundError
from app.models.coding_standard import CodingStandard

router = APIRouter()


class StandardResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    version: str | None = None
    effective_date: date | None = None
    is_active: bool
    metadata_: dict | None = None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[StandardResponse])
async def list_standards(
    user: AuthUser,
    db: DBSession,
):
    """List all available coding standards."""
    result = await db.execute(
        select(CodingStandard)
        .where(CodingStandard.is_active.is_(True))
        .order_by(CodingStandard.name)
    )
    standards = result.scalars().all()
    return [StandardResponse.model_validate(s) for s in standards]


@router.get("/{code}", response_model=StandardResponse)
async def get_standard(
    code: str,
    user: AuthUser,
    db: DBSession,
):
    """Get details for a specific coding standard."""
    result = await db.execute(
        select(CodingStandard).where(CodingStandard.code == code)
    )
    standard = result.scalar_one_or_none()
    if standard is None:
        raise NotFoundError(f"Standard '{code}' not found")
    return StandardResponse.model_validate(standard)
