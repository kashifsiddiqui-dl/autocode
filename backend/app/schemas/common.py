"""Shared Pydantic v2 schemas: pagination, error responses, base models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


class ErrorDetail(BaseModel):
    field: str | None = None
    issue: str
    detail: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None
