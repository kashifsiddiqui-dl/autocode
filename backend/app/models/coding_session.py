"""CodingSession model — a single auto-coding request and its lifecycle."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, UUIDMixin


class CodingSession(UUIDMixin, TenantMixin, Base):
    __tablename__ = "coding_sessions"

    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    standard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coding_standards.id", ondelete="RESTRICT"),
        nullable=False,
    )

    clinical_input: Mapped[str] = mapped_column(Text, nullable=False)
    patient_demographics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(String(30), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'")
    )  # pending | processing | completed | error
    rag_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    patient: Mapped["Patient | None"] = relationship("Patient", lazy="selectin")
    user: Mapped["User"] = relationship("User", lazy="selectin")
    standard: Mapped["CodingStandard"] = relationship("CodingStandard", lazy="selectin")
    results: Mapped[list["CodingResult"]] = relationship(
        "CodingResult",
        back_populates="session",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="CodingResult.sequence_order",
    )
