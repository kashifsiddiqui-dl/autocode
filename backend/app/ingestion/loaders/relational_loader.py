"""Relational database loader for ICD-10-CM data.

Bulk inserts parsed ICD-10-CM codes and index entries into PostgreSQL
using SQLAlchemy async sessions with ON CONFLICT DO UPDATE semantics.
"""

from __future__ import annotations

import json
import logging
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.parsers.index import IndexEntryData
from app.ingestion.parsers.tabular import IcdCodeData

logger = logging.getLogger(__name__)

# Batch size for bulk inserts
BATCH_SIZE = 1000


def _safe_int(value: str, default: int | None = None) -> int | None:
    """Safely convert a string to int, returning default on failure."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


class RelationalLoader:
    """Loads parsed ICD-10-CM data into PostgreSQL tables.

    Uses raw SQL with ON CONFLICT DO UPDATE to support idempotent ingestion
    (re-running the pipeline updates existing records rather than failing).

    Column mapping is aligned with the SQLAlchemy models in:
    - app.models.icd_code.IcdCode
    - app.models.icd_index_entry.IcdIndexEntry
    """

    async def load_codes(
        self,
        session: AsyncSession,
        codes: list[IcdCodeData],
        standard_id: UUID,
    ) -> int:
        """Bulk insert ICD-10-CM codes into the icd_codes table.

        Args:
            session: SQLAlchemy async session.
            codes: List of parsed IcdCodeData objects.
            standard_id: UUID of the coding standard record.

        Returns:
            Number of codes inserted/updated.
        """
        logger.info("Loading %d codes into icd_codes table", len(codes))

        total_loaded = 0
        for batch_start in range(0, len(codes), BATCH_SIZE):
            batch = codes[batch_start : batch_start + BATCH_SIZE]
            values = []
            for seq_num, code_data in enumerate(batch, start=batch_start + 1):
                # Model column types:
                #   chapter_num: Integer (nullable)
                #   inclusion_terms: ARRAY(Text) (nullable)
                #   excludes1, excludes2: JSON (nullable) - store as list
                #   code_first, use_additional_code, code_also: ARRAY(Text) (nullable)
                #   seven_chr_def: JSON (nullable) - store as list of dicts
                values.append(
                    {
                        "id": str(uuid4()),
                        "standard_id": str(standard_id),
                        "code": code_data.code,
                        "description": code_data.description,
                        "short_description": code_data.short_description,
                        "parent_code": code_data.parent_code,
                        "is_billable": code_data.is_billable,
                        "chapter_num": _safe_int(code_data.chapter_num),
                        "chapter_name": code_data.chapter_name,
                        "section_id": code_data.section_id,
                        "section_name": code_data.section_name,
                        "code_level": code_data.code_level,
                        "sequence_num": seq_num,
                        "inclusion_terms": code_data.inclusion_terms or None,
                        "excludes1": json.dumps(code_data.excludes1) if code_data.excludes1 else None,
                        "excludes2": json.dumps(code_data.excludes2) if code_data.excludes2 else None,
                        "code_first": code_data.code_first or None,
                        "use_additional_code": code_data.use_additional_code or None,
                        "code_also": code_data.code_also or None,
                        "seven_chr_note": code_data.seven_chr_note,
                        "seven_chr_def": (
                            json.dumps(code_data.seven_chr_def)
                            if code_data.seven_chr_def
                            else None
                        ),
                    }
                )

            # The unique constraint is (standard_id, code) per ix_icd_codes_standard_code
            stmt = text("""
                INSERT INTO icd_codes (
                    id, standard_id, code, description, short_description,
                    parent_code, is_billable, chapter_num, chapter_name,
                    section_id, section_name, code_level, sequence_num,
                    inclusion_terms, excludes1, excludes2,
                    code_first, use_additional_code, code_also,
                    seven_chr_note, seven_chr_def
                ) VALUES (
                    :id::uuid, :standard_id::uuid, :code, :description, :short_description,
                    :parent_code, :is_billable, :chapter_num, :chapter_name,
                    :section_id, :section_name, :code_level, :sequence_num,
                    :inclusion_terms, :excludes1::jsonb, :excludes2::jsonb,
                    :code_first, :use_additional_code, :code_also,
                    :seven_chr_note, :seven_chr_def::jsonb
                )
                ON CONFLICT (standard_id, code) DO UPDATE SET
                    description = EXCLUDED.description,
                    short_description = EXCLUDED.short_description,
                    parent_code = EXCLUDED.parent_code,
                    is_billable = EXCLUDED.is_billable,
                    chapter_num = EXCLUDED.chapter_num,
                    chapter_name = EXCLUDED.chapter_name,
                    section_id = EXCLUDED.section_id,
                    section_name = EXCLUDED.section_name,
                    code_level = EXCLUDED.code_level,
                    sequence_num = EXCLUDED.sequence_num,
                    inclusion_terms = EXCLUDED.inclusion_terms,
                    excludes1 = EXCLUDED.excludes1,
                    excludes2 = EXCLUDED.excludes2,
                    code_first = EXCLUDED.code_first,
                    use_additional_code = EXCLUDED.use_additional_code,
                    code_also = EXCLUDED.code_also,
                    seven_chr_note = EXCLUDED.seven_chr_note,
                    seven_chr_def = EXCLUDED.seven_chr_def
            """)

            await session.execute(stmt, values)
            total_loaded += len(batch)
            logger.info(
                "Loaded codes batch: %d/%d (%d%%)",
                total_loaded,
                len(codes),
                int(total_loaded / len(codes) * 100),
            )

        await session.commit()
        logger.info("Finished loading %d codes", total_loaded)
        return total_loaded

    async def load_index_entries(
        self,
        session: AsyncSession,
        entries: list[IndexEntryData],
        standard_id: UUID,
    ) -> int:
        """Bulk insert index entries into the icd_index_entries table.

        Uses simple INSERT (no ON CONFLICT) since the icd_index_entries table
        does not define a multi-column unique constraint. A DELETE + INSERT
        strategy is used per standard_id to ensure idempotency.

        Args:
            session: SQLAlchemy async session.
            entries: List of parsed IndexEntryData objects.
            standard_id: UUID of the coding standard record.

        Returns:
            Number of entries inserted.
        """
        logger.info("Loading %d index entries into icd_index_entries table", len(entries))

        # Delete existing entries for this standard to support re-ingestion
        delete_stmt = text(
            "DELETE FROM icd_index_entries WHERE standard_id = :standard_id"
        )
        await session.execute(delete_stmt, {"standard_id": str(standard_id)})
        logger.info("Cleared existing index entries for standard %s", standard_id)

        total_loaded = 0
        for batch_start in range(0, len(entries), BATCH_SIZE):
            batch = entries[batch_start : batch_start + BATCH_SIZE]
            values = []
            for entry in batch:
                values.append(
                    {
                        "id": str(uuid4()),
                        "standard_id": str(standard_id),
                        "term": entry.term,
                        "parent_term": entry.parent_term,
                        "level": entry.level,
                        "code": entry.code,
                        "see_reference": entry.see_reference,
                        "see_also_reference": entry.see_also_reference,
                        "index_type": entry.index_type,
                        "matrix_codes": (
                            json.dumps(entry.matrix_codes)
                            if entry.matrix_codes
                            else None
                        ),
                    }
                )

            stmt = text("""
                INSERT INTO icd_index_entries (
                    id, standard_id, term, parent_term, level,
                    code, see_reference, see_also_reference,
                    index_type, matrix_codes
                ) VALUES (
                    :id::uuid, :standard_id::uuid, :term, :parent_term, :level,
                    :code, :see_reference, :see_also_reference,
                    :index_type, :matrix_codes::jsonb
                )
            """)

            await session.execute(stmt, values)
            total_loaded += len(batch)

            if total_loaded % 5000 == 0 or total_loaded == len(entries):
                logger.info(
                    "Loaded index entries batch: %d/%d (%d%%)",
                    total_loaded,
                    len(entries),
                    int(total_loaded / len(entries) * 100),
                )

        await session.commit()
        logger.info("Finished loading %d index entries", total_loaded)
        return total_loaded
