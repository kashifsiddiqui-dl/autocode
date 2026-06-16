"""Admin endpoints — user management, usage stats, audit log, tenant settings."""

from __future__ import annotations

import math
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AdminUser, DBSession, require_role
from app.core.exceptions import NotFoundError
from app.models.audit_log import AuditLog
from app.models.coding_result import CodingResult
from app.models.coding_session import CodingSession
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.admin import (
    AuditLogEntry,
    TenantSettings,
    UserCreate,
    UserResponse,
    UserUpdate,
    UsageStats,
)
from app.schemas.common import PaginatedResponse
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("/users", response_model=PaginatedResponse[UserResponse])
async def list_users(
    user: AdminUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    """List all users in the tenant."""
    base = select(User).where(User.tenant_id == user.tenant_id)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * size
    rows_stmt = base.order_by(User.full_name).offset(offset).limit(size)
    result = await db.execute(rows_stmt)
    users = result.scalars().all()

    return PaginatedResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size else 0,
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(
    body: UserCreate,
    admin: AdminUser,
    db: DBSession,
    request: Request,
):
    """Invite a new user to the tenant."""
    new_user = User(
        tenant_id=admin.tenant_id,
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        external_id=body.external_id,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    audit = AuditService(db)
    await audit.log_action(
        tenant_id=admin.tenant_id,
        user_id=admin.id,
        action="user.invited",
        resource_type="User",
        resource_id=str(new_user.id),
        details={"email": body.email, "role": body.role},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return UserResponse.model_validate(new_user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    admin: AdminUser,
    db: DBSession,
    request: Request,
):
    """Update a user's role or active status."""
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == admin.tenant_id)
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise NotFoundError(f"User {user_id} not found")

    changes: dict = {}
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        old = getattr(target, field)
        if old != value:
            changes[field] = {"old": old, "new": value}
            setattr(target, field, value)

    await db.flush()

    if changes:
        audit = AuditService(db)
        await audit.log_action(
            tenant_id=admin.tenant_id,
            user_id=admin.id,
            action="user.updated",
            resource_type="User",
            resource_id=str(user_id),
            details=changes,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

    return UserResponse.model_validate(target)


@router.get("/usage", response_model=UsageStats)
async def get_usage(
    admin: AdminUser,
    db: DBSession,
):
    """Get usage statistics for the tenant."""
    total_sessions = (
        await db.execute(
            select(func.count())
            .select_from(CodingSession)
            .where(CodingSession.tenant_id == admin.tenant_id)
        )
    ).scalar_one()

    total_codes = (
        await db.execute(
            select(func.count())
            .select_from(CodingResult)
            .join(CodingSession, CodingResult.session_id == CodingSession.id)
            .where(CodingSession.tenant_id == admin.tenant_id)
        )
    ).scalar_one()

    active_users = (
        await db.execute(
            select(func.count())
            .select_from(User)
            .where(User.tenant_id == admin.tenant_id, User.is_active.is_(True))
        )
    ).scalar_one()

    from datetime import timezone
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    sessions_this_month = (
        await db.execute(
            select(func.count())
            .select_from(CodingSession)
            .where(
                CodingSession.tenant_id == admin.tenant_id,
                CodingSession.created_at >= month_start,
            )
        )
    ).scalar_one()

    return UsageStats(
        tenant_id=admin.tenant_id,
        total_sessions=total_sessions,
        total_codes_generated=total_codes,
        active_users=active_users,
        sessions_this_month=sessions_this_month,
        llm_requests_this_month=sessions_this_month,
        period_start=month_start,
        period_end=now,
    )


@router.get("/audit-log", response_model=PaginatedResponse[AuditLogEntry])
async def list_audit_log(
    admin: AdminUser,
    db: DBSession,
    action: str | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
):
    """View the audit log for this tenant."""
    svc = AuditService(db)
    entries, total = await svc.get_audit_log(
        admin.tenant_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        since=since,
        until=until,
        page=page,
        size=size,
    )

    return PaginatedResponse(
        items=[AuditLogEntry.model_validate(e) for e in entries],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size else 0,
    )


@router.patch("/settings", response_model=dict)
async def update_tenant_settings(
    body: TenantSettings,
    admin: AdminUser,
    db: DBSession,
    request: Request,
):
    """Update tenant-level settings."""
    result = await db.execute(select(Tenant).where(Tenant.id == admin.tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise NotFoundError("Tenant not found")

    changes: dict = {}
    update_data = body.model_dump(exclude_unset=True)

    if "settings" in update_data and update_data["settings"] is not None:
        current = tenant.settings or {}
        current.update(update_data.pop("settings"))
        tenant.settings = current
        changes["settings"] = "updated"

    for field, value in update_data.items():
        if hasattr(tenant, field):
            old = getattr(tenant, field)
            if old != value:
                changes[field] = {"old": old, "new": value}
                setattr(tenant, field, value)

    await db.flush()

    if changes:
        audit = AuditService(db)
        await audit.log_action(
            tenant_id=admin.tenant_id,
            user_id=admin.id,
            action="tenant.settings_updated",
            resource_type="Tenant",
            resource_id=str(admin.tenant_id),
            details=changes,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

    return {"status": "updated", "changes": changes}
