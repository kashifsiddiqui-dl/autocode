"""Pydantic v2 schemas for coding analysis endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import OrmBase


class PatientContext(BaseModel):
    name: str | None = None
    dob: str | None = None
    mrn: str | None = None
    gender: str | None = None


class CodingOptions(BaseModel):
    max_results: int = Field(default=10, ge=1, le=25)
    min_confidence: float = Field(default=0.3, ge=0.0, le=1.0)
    billable_only: bool = False
    chapter_filter: list[int] | None = None
    standard: str = "icd10cm"
    version: str = "latest"
    llm_provider: str | None = None
    llm_model: str | None = None


class CodingRequest(BaseModel):
    clinical_text: str = Field(..., min_length=10, max_length=10000)
    session_id: uuid.UUID | None = None
    patient_id: uuid.UUID | None = None
    patient: PatientContext | None = None
    options: CodingOptions = Field(default_factory=CodingOptions)


class HierarchyInfo(BaseModel):
    chapter_num: int | None = None
    chapter_name: str | None = None
    section_id: str | None = None
    section_name: str | None = None
    category: str | None = None
    parent_code: str | None = None


class CodeSuggestion(BaseModel):
    code: str
    description: str
    confidence: float
    reasoning: str | None = None
    is_billable: bool = True
    is_validated: bool = False
    hierarchy: HierarchyInfo | None = None
    excludes1: list[str] | None = None
    excludes2: list[str] | None = None
    coding_instructions: str | None = None
    seventh_char: str | None = None
    seventh_char_desc: str | None = None
    source_chunks: list[str] | None = None


class CodingResultResponse(OrmBase):
    id: uuid.UUID
    icd_code: str
    icd_description: str
    confidence_score: float
    retrieval_score: float | None = None
    rationale: str | None = None
    coding_instructions: str | None = None
    seventh_char: str | None = None
    seventh_char_desc: str | None = None
    is_validated: bool
    is_primary: bool
    sequence_order: int
    created_at: datetime


class CodingSessionResponse(OrmBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    patient_id: uuid.UUID | None = None
    user_id: uuid.UUID
    clinical_input: str
    patient_demographics: dict | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    status: str
    rag_metadata: dict | None = None
    created_at: datetime
    completed_at: datetime | None = None
    results: list[CodingResultResponse] = []


class CodingSessionSummary(OrmBase):
    id: uuid.UUID
    patient_id: uuid.UUID | None = None
    status: str
    llm_provider: str | None = None
    llm_model: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    result_count: int = 0


class FeedbackRequest(BaseModel):
    result_id: uuid.UUID | None = None
    code: str | None = None
    action: str = Field(..., pattern="^(accepted|rejected|corrected)$")
    reason: str | None = None
    corrected_code: str | None = None
