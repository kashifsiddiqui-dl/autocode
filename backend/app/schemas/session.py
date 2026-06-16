"""Pydantic schemas for session feedback."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class SessionFeedback(BaseModel):
    """User feedback on a single code result within a session."""

    code_result_id: uuid.UUID
    is_correct: bool
    correction: str | None = Field(default=None, max_length=20)
