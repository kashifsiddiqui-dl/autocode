"""Tenant context management for row-level security."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_tenant_context(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Set the PostgreSQL session variable ``app.current_tenant_id``.

    RLS policies on tenant-scoped tables can reference this via:
        ``current_setting('app.current_tenant_id')::uuid``
    """
    await session.execute(
        text("SET LOCAL app.current_tenant_id = :tid"),
        {"tid": str(tenant_id)},
    )


class TenantContext:
    """Dependency-injectable tenant context for FastAPI endpoints."""

    def __init__(self, tenant_id: uuid.UUID) -> None:
        self.tenant_id = tenant_id

    async def apply(self, session: AsyncSession) -> None:
        """Apply the tenant context to the given database session."""
        await set_tenant_context(session, self.tenant_id)
