"""CodingResult model — individual code suggestions within a session."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class CodingResult(UUIDMixin, Base):
    __tablename__ = "coding_results"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coding_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    icd_code: Mapped[str] = mapped_column(String(20), nullable=False)
    icd_description: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    retrieval_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    coding_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    seventh_char: Mapped[str | None] = mapped_column(String(5), nullable=True)
    seventh_char_desc: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_validated: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    # Relationships
    session: Mapped["CodingSession"] = relationship(
        "CodingSession", back_populates="results", lazy="selectin"
    )
