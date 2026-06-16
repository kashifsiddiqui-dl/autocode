"""Pydantic schemas for patient CRUD operations."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    """Payload for creating a new patient."""

    mrn: str = Field(..., max_length=50)
    first_name: str = Field(..., max_length=255)
    last_name: str = Field(..., max_length=255)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=20)
    demographics: dict | None = None


class PatientUpdate(BaseModel):
    """Payload for updating an existing patient (all fields optional)."""

    mrn: str | None = Field(default=None, max_length=50)
    first_name: str | None = Field(default=None, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=20)
    demographics: dict | None = None


class PatientResponse(BaseModel):
    """Full patient record."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    mrn: str
    first_name: str
    last_name: str
    date_of_birth: date | None = None
    gender: str | None = None
    demographics: dict | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class PatientList(BaseModel):
    """Lightweight patient representation for list endpoints."""

    id: uuid.UUID
    mrn: str
    first_name: str
    last_name: str
    date_of_birth: date | None = None
    gender: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
