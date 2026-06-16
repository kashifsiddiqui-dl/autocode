"""Pydantic schemas for export operations."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class ExportFormat(StrEnum):
    PDF = "pdf"
    CSV = "csv"
    JSON = "json"
    HL7 = "hl7"


class ExportOptions(BaseModel):
    include_rejected: bool = False
    include_reasoning: bool = True
    include_confidence: bool = True
    include_audit_trail: bool = True
    include_clinical_notes: bool = True


class ExportRequest(BaseModel):
    session_id: uuid.UUID
    format: ExportFormat = ExportFormat.PDF
    options: ExportOptions | None = None


class ExportResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    format: str
    status: str
    file_path: str | None = None
    file_size: int | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    download_url: str | None = None

    model_config = {"from_attributes": True}
