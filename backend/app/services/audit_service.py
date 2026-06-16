"""Audit logging service for compliance and traceability."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Provides structured audit logging backed by the ``audit_logs`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log_action(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Create an audit log entry.

        Args:
            tenant_id: Tenant that owns this event.
            user_id: User who performed the action (None for system events).
            action: Short verb phrase, e.g. ``"coding_session.created"``.
            resource_type: Entity type, e.g. ``"CodingSession"``.
            resource_id: Primary key of the affected resource.
            details: Arbitrary JSON payload with extra context.
            ip_address: Client IP address.
            user_agent: Client User-Agent string.

        Returns:
            The persisted ``AuditLog`` instance.
        """
        entry = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._session.add(entry)
        await self._session.flush()
        logger.debug(
            "Audit: tenant=%s user=%s action=%s resource=%s/%s",
            tenant_id,
            user_id,
            action,
            resource_type,
            resource_id,
        )
        return entry

    async def get_audit_log(
        self,
        tenant_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        page: int = 1,
        size: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """Query audit log entries with optional filters and pagination.

        Args:
            tenant_id: Required tenant scope.
            user_id: Filter by acting user.
            action: Filter by action string (exact match).
            resource_type: Filter by resource type.
            resource_id: Filter by resource ID.
            since: Only entries created at or after this time.
            until: Only entries created before this time.
            page: 1-based page number.
            size: Page size.

        Returns:
            Tuple of (entries, total_count).
        """
        base = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

        if user_id is not None:
            base = base.where(AuditLog.user_id == user_id)
        if action is not None:
            base = base.where(AuditLog.action == action)
        if resource_type is not None:
            base = base.where(AuditLog.resource_type == resource_type)
        if resource_id is not None:
            base = base.where(AuditLog.resource_id == str(resource_id))
        if since is not None:
            base = base.where(AuditLog.created_at >= since)
        if until is not None:
            base = base.where(AuditLog.created_at < until)

        # Total count
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        # Paginated results, newest first
        offset = (page - 1) * size
        rows_stmt = (
            base.order_by(AuditLog.created_at.desc()).offset(offset).limit(size)
        )
        result = await self._session.execute(rows_stmt)
        entries = list(result.scalars().all())

        return entries, total
