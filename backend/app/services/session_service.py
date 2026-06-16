"""Session service — manages coding session lifecycle and feedback.

TODO: Implement once the coding pipeline and feedback loop are wired.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coding_result import CodingResult
from app.models.coding_session import CodingSession
from app.schemas.session import SessionFeedback


class SessionService:
    """Manages coding session queries and user feedback."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_session(
        self,
        session_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> CodingSession | None:
        """Retrieve a coding session with its results."""
        stmt = select(CodingSession).where(
            CodingSession.id == session_id,
            CodingSession.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        tenant_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[CodingSession], int]:
        """List coding sessions with optional filters and pagination.

        TODO: Add date range filtering and sorting options.
        """
        base = select(CodingSession).where(CodingSession.tenant_id == tenant_id)

        if user_id is not None:
            base = base.where(CodingSession.user_id == user_id)
        if status is not None:
            base = base.where(CodingSession.status == status)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * size
        rows_stmt = base.order_by(CodingSession.created_at.desc()).offset(offset).limit(size)
        result = await self._session.execute(rows_stmt)
        sessions = list(result.scalars().all())

        return sessions, total

    async def submit_feedback(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        feedback: SessionFeedback,
    ) -> CodingResult | None:
        """Record user feedback on a coding result.

        TODO: Implement feedback persistence and optional re-ranking
              based on user corrections.
        """
        stmt = select(CodingResult).where(CodingResult.id == feedback.code_result_id)
        result = await self._session.execute(stmt)
        coding_result = result.scalar_one_or_none()

        if coding_result is None:
            return None

        coding_result.is_validated = feedback.is_correct
        if feedback.correction is not None:
            coding_result.icd_code = feedback.correction

        await self._session.flush()
        return coding_result

    async def delete_session(
        self,
        session_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Delete a coding session and its results (cascade).

        TODO: Add audit logging on deletion.
        """
        session = await self.get_session(session_id, tenant_id)
        if session is None:
            return False

        await self._session.delete(session)
        await self._session.flush()
        return True
