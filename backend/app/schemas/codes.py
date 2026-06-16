"""Pydantic v2 schemas for code browsing and search endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import OrmBase


class CodeResponse(OrmBase):
    id: uuid.UUID
    code: str
    description: str
    short_description: str | None = None
    is_billable: bool
    chapter_num: int | None = None
    chapter_name: str | None = None
    section_id: str | None = None
    section_name: str | None = None
    parent_code: str | None = None
    code_level: int | None = None
    inclusion_terms: list[str] | None = None
    excludes1: dict | None = None
    excludes2: dict | None = None
    code_first: list[str] | None = None
    use_additional_code: list[str] | None = None
    code_also: list[str] | None = None
    seven_chr_note: str | None = None
    seven_chr_def: dict | None = None


class CodeSummary(OrmBase):
    id: uuid.UUID
    code: str
    description: str
    is_billable: bool
    chapter_num: int | None = None
    parent_code: str | None = None


class HierarchyNode(BaseModel):
    code: str
    description: str
    is_billable: bool
    level: int | None = None


class CodeHierarchyResponse(BaseModel):
    code: str
    description: str
    parents: list[HierarchyNode] = []
    siblings: list[HierarchyNode] = []
    children: list[HierarchyNode] = []


class CodeSearchParams(BaseModel):
    q: str = Field(..., min_length=2, max_length=500)
    chapter: int | None = None
    billable: bool | None = None
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class SemanticSearchResult(BaseModel):
    code: str
    description: str
    is_billable: bool
    score: float
    chapter_num: int | None = None
