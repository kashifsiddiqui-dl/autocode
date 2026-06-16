"""IcdIndexEntry model — alphabetical index entries (disease, drug, neoplasm, eindex)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class IcdIndexEntry(UUIDMixin, Base):
    __tablename__ = "icd_index_entries"
    __table_args__ = (
        Index("ix_icd_index_entries_index_type", "index_type"),
    )

    standard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coding_standards.id", ondelete="CASCADE"),
        nullable=False,
    )
    index_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # disease | drug | neoplasm | eindex
    term: Mapped[str] = mapped_column(Text, nullable=False)
    parent_term: Mapped[str | None] = mapped_column(Text, nullable=True)
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    see_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    see_also_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    matrix_codes: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    # Relationships
    standard: Mapped["CodingStandard"] = relationship("CodingStandard", lazy="selectin")
