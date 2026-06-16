"""Pydantic schemas for admin operations."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., max_length=255)
    role: str = Field(default="coder", pattern=r"^(admin|coder|viewer)$")
    external_id: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    role: str | None = Field(default=None, pattern=r"^(admin|coder|viewer)$")
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantSettings(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    sso_provider: str | None = Field(default=None, max_length=50)
    sso_config: dict | None = None
    settings: dict | None = None


class UsageStats(BaseModel):
    tenant_id: uuid.UUID
    total_sessions: int = 0
    total_codes_generated: int = 0
    active_users: int = 0
    sessions_this_month: int = 0
    llm_requests_this_month: int = 0
    period_start: datetime | None = None
    period_end: datetime | None = None


class AuditLogEntry(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict | None = None
    ip_address: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
