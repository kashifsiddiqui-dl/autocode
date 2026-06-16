"""Health and readiness endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.db.vector import qdrant_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness() -> dict[str, str]:
    """Liveness probe — returns 200 if the process is running."""
    return {"status": "ok"}


@router.get("/ready")
async def readiness() -> dict[str, str | dict[str, str]]:
    """Readiness probe — checks PostgreSQL and Qdrant connectivity."""
    checks: dict[str, str] = {}

    # PostgreSQL
    try:
        async for session in get_session():
            await session.execute(text("SELECT 1"))
            checks["postgres"] = "ok"
    except Exception:
        logger.exception("Readiness: PostgreSQL check failed")
        checks["postgres"] = "unavailable"

    # Qdrant
    try:
        client = qdrant_manager.get_client()
        collections = await client.get_collections()
        checks["qdrant"] = "ok"
    except Exception:
        logger.exception("Readiness: Qdrant check failed")
        checks["qdrant"] = "unavailable"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ready" if all_ok else "degraded", "checks": checks}
