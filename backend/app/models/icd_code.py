"""IcdCode model — individual ICD-10-CM codes with full tabular metadata."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class IcdCode(UUIDMixin, Base):
    __tablename__ = "icd_codes"
    __table_args__ = (
        Index("ix_icd_codes_standard_code", "standard_id", "code", unique=True),
        Index("ix_icd_codes_code", "code"),
        Index("ix_icd_codes_parent_code", "parent_code"),
        Index("ix_icd_codes_chapter_num", "chapter_num"),
        Index("ix_icd_codes_is_billable", "is_billable"),
    )

    standard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("coding_standards.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    parent_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    short_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_billable: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)

    chapter_num: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chapter_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    section_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    section_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    code_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sequence_num: Mapped[int | None] = mapped_column(Integer, nullable=True)

    inclusion_terms: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    excludes1: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    excludes2: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    code_first: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    use_additional_code: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    code_also: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)

    seven_chr_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    seven_chr_def: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    # Relationships
    standard: Mapped["CodingStandard"] = relationship("CodingStandard", lazy="selectin")
