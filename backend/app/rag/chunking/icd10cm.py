"""ICD-10-CM specific chunking strategy.

Converts parsed ICD-10-CM data (codes, index entries, drug/neoplasm tables)
into semantically rich text chunks for vector embedding and RAG retrieval.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from app.ingestion.parsers.index import IndexEntryData
from app.ingestion.parsers.tabular import IcdCodeData
from app.rag.chunking.strategy import ChunkData, ChunkingStrategy

logger = logging.getLogger(__name__)


def _generate_chunk_id(prefix: str, key: str) -> str:
    """Generate a deterministic chunk ID from a prefix and key."""
    hash_val = hashlib.sha256(f"{prefix}:{key}".encode()).hexdigest()[:16]
    return f"{prefix}_{hash_val}"


class ICD10CMChunker(ChunkingStrategy):
    """Chunking strategy for ICD-10-CM coding data.

    Produces rich text chunks that include hierarchical context, clinical
    annotations, and cross-references to maximize retrieval accuracy.
    """

    def __init__(self, standard_id: str = "icd10cm") -> None:
        self.standard_id = standard_id
        # Built during chunk_codes to support sibling/hierarchy lookups
        self._code_map: dict[str, IcdCodeData] = {}
        self._children_map: dict[str | None, list[str]] = {}

    def chunk(self, data: Any) -> list[ChunkData]:
        """Generic chunk method - delegates based on data type."""
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, IcdCodeData):
                return self.chunk_codes(data)
            if isinstance(first, IndexEntryData):
                if first.index_type == "drug":
                    return self.chunk_drug_entries(data)
                if first.index_type == "neoplasm":
                    return self.chunk_neoplasm_entries(data)
                return self.chunk_index_entries(data)
        return []

    def chunk_codes(self, codes: list[IcdCodeData]) -> list[ChunkData]:
        """Create rich text chunks for billable ICD-10-CM codes.

        Each chunk includes the full hierarchical context, clinical annotations,
        sibling codes, and coding instructions to provide maximum context
        for retrieval.

        Args:
            codes: List of all IcdCodeData from the tabular parser.

        Returns:
            List of ChunkData for billable codes only.
        """
        logger.info("Chunking %d codes (billable only)", len(codes))

        # Build lookup maps for hierarchy navigation
        self._code_map = {c.code: c for c in codes}
        self._children_map = {}
        for c in codes:
            self._children_map.setdefault(c.parent_code, []).append(c.code)

        chunks: list[ChunkData] = []
        billable_count = 0

        for code_data in codes:
            if not code_data.is_billable:
                continue

            billable_count += 1
            text = self._build_code_chunk_text(code_data)

            chunk = ChunkData(
                chunk_id=_generate_chunk_id("icd10cm_code", code_data.code),
                chunk_type="code",
                text=text,
                metadata={
                    "code": code_data.code,
                    "description": code_data.description,
                    "is_billable": True,
                    "chapter_num": code_data.chapter_num,
                    "chapter_name": code_data.chapter_name,
                    "section_id": code_data.section_id,
                    "section_name": code_data.section_name,
                    "parent_code": code_data.parent_code,
                    "code_level": code_data.code_level,
                },
                code=code_data.code,
                standard_id=self.standard_id,
            )
            chunks.append(chunk)

        logger.info("Created %d code chunks from %d billable codes", len(chunks), billable_count)
        return chunks

    def _build_code_chunk_text(self, code_data: IcdCodeData) -> str:
        """Build the rich text representation for a single code."""
        lines: list[str] = []

        lines.append(f"Code: {code_data.code}")
        lines.append(f"Description: {code_data.description}")

        # Parent category info
        if code_data.parent_code and code_data.parent_code in self._code_map:
            parent = self._code_map[code_data.parent_code]
            lines.append(f"Category: {parent.code} - {parent.description}")

        lines.append(f"Section: {code_data.section_id} - {code_data.section_name}")
        lines.append(f"Chapter: {code_data.chapter_num} - {code_data.chapter_name}")

        # 7th character definitions
        if code_data.seven_chr_def:
            defs = "; ".join(
                f"{d['char']}={d['description']}" for d in code_data.seven_chr_def
            )
            note = code_data.seven_chr_note or "7th character required"
            lines.append(f"7th Character Required: {note}: {defs}")

        # Clinical annotations
        if code_data.inclusion_terms:
            lines.append(f"Inclusion Terms: {'; '.join(code_data.inclusion_terms)}")

        if code_data.includes:
            lines.append(f"Includes: {'; '.join(code_data.includes)}")

        if code_data.excludes1:
            lines.append(f"Excludes1: {'; '.join(code_data.excludes1)}")

        if code_data.excludes2:
            lines.append(f"Excludes2: {'; '.join(code_data.excludes2)}")

        if code_data.code_first:
            lines.append(f"Code First: {'; '.join(code_data.code_first)}")

        if code_data.use_additional_code:
            lines.append(f"Use Additional Code: {'; '.join(code_data.use_additional_code)}")

        if code_data.code_also:
            lines.append(f"Code Also: {'; '.join(code_data.code_also)}")

        # Hierarchy chain
        hierarchy = self._build_hierarchy_chain(code_data.code)
        if hierarchy:
            lines.append(f"Parent: {' > '.join(hierarchy)}")

        # Sibling codes
        siblings = self._get_siblings(code_data)
        if siblings:
            sibling_strs = [
                f"{s.code} ({s.description})" for s in siblings if s.code != code_data.code
            ]
            if sibling_strs:
                lines.append(f"Siblings: {'; '.join(sibling_strs)}")

        return "\n".join(lines)

    def _build_hierarchy_chain(self, code: str) -> list[str]:
        """Build the chain of parent codes from root to this code's parent."""
        chain: list[str] = []
        current_code = code
        visited: set[str] = set()

        while current_code in self._code_map:
            if current_code in visited:
                break
            visited.add(current_code)
            parent_code = self._code_map[current_code].parent_code
            if parent_code and parent_code in self._code_map:
                parent = self._code_map[parent_code]
                chain.append(f"{parent.code} ({parent.description})")
                current_code = parent_code
            else:
                break

        chain.reverse()
        return chain

    def _get_siblings(self, code_data: IcdCodeData) -> list[IcdCodeData]:
        """Get sibling codes (codes sharing the same parent)."""
        if code_data.parent_code is None:
            return []
        sibling_codes = self._children_map.get(code_data.parent_code, [])
        return [
            self._code_map[sc]
            for sc in sibling_codes
            if sc in self._code_map and sc != code_data.code
        ]

    def chunk_index_entries(self, entries: list[IndexEntryData]) -> list[ChunkData]:
        """Create text chunks for disease/eindex entries.

        Args:
            entries: List of IndexEntryData from the index or eindex parser.

        Returns:
            List of ChunkData for index entries.
        """
        index_type = entries[0].index_type if entries else "disease"
        logger.info("Chunking %d %s index entries", len(entries), index_type)

        chunks: list[ChunkData] = []
        for entry in entries:
            text = self._build_index_chunk_text(entry)
            chunk_key = f"{entry.index_type}:{entry.term}:{entry.parent_term or ''}:{entry.level}"

            chunk = ChunkData(
                chunk_id=_generate_chunk_id(f"icd10cm_{entry.index_type}", chunk_key),
                chunk_type=f"{entry.index_type}_index",
                text=text,
                metadata={
                    "term": entry.term,
                    "parent_term": entry.parent_term,
                    "level": entry.level,
                    "code": entry.code,
                    "index_type": entry.index_type,
                },
                code=entry.code,
                standard_id=self.standard_id,
            )
            chunks.append(chunk)

        logger.info("Created %d %s index chunks", len(chunks), index_type)
        return chunks

    def _build_index_chunk_text(self, entry: IndexEntryData) -> str:
        """Build text representation for a single index entry."""
        lines: list[str] = []
        lines.append(f"Term: {entry.term}")

        if entry.parent_term:
            lines.append(f"Parent: {entry.parent_term}")

        if entry.code:
            lines.append(f"Code: {entry.code}")

        if entry.see_reference:
            lines.append(f"See: {entry.see_reference}")

        if entry.see_also_reference:
            lines.append(f"See Also: {entry.see_also_reference}")

        if entry.nemod:
            lines.append(f"Modifier: {entry.nemod}")

        return "\n".join(lines)

    def chunk_drug_entries(self, entries: list[IndexEntryData]) -> list[ChunkData]:
        """Create text chunks for drug table entries.

        Each chunk includes the substance name and its full matrix of codes
        across poisoning categories, adverse effects, and underdosing.

        Args:
            entries: List of IndexEntryData from the drug parser.

        Returns:
            List of ChunkData for drug table entries.
        """
        logger.info("Chunking %d drug table entries", len(entries))

        chunks: list[ChunkData] = []
        for entry in entries:
            text = self._build_drug_chunk_text(entry)
            chunk_key = f"drug:{entry.term}:{entry.parent_term or ''}:{entry.level}"

            chunk = ChunkData(
                chunk_id=_generate_chunk_id("icd10cm_drug", chunk_key),
                chunk_type="drug_entry",
                text=text,
                metadata={
                    "term": entry.term,
                    "parent_term": entry.parent_term,
                    "level": entry.level,
                    "index_type": "drug",
                    "matrix_codes": entry.matrix_codes,
                },
                code=None,
                standard_id=self.standard_id,
            )
            chunks.append(chunk)

        logger.info("Created %d drug entry chunks", len(chunks))
        return chunks

    def _build_drug_chunk_text(self, entry: IndexEntryData) -> str:
        """Build text representation for a drug table entry."""
        lines: list[str] = []
        lines.append(f"Substance: {entry.term}")

        if entry.parent_term:
            lines.append(f"Parent Substance: {entry.parent_term}")

        if entry.matrix_codes:
            for col_name, code in entry.matrix_codes.items():
                lines.append(f"{col_name}: {code}")

        return "\n".join(lines)

    def chunk_neoplasm_entries(self, entries: list[IndexEntryData]) -> list[ChunkData]:
        """Create text chunks for neoplasm table entries.

        Each chunk includes the anatomical site and its full matrix of codes
        across neoplasm behavior types.

        Args:
            entries: List of IndexEntryData from the neoplasm parser.

        Returns:
            List of ChunkData for neoplasm table entries.
        """
        logger.info("Chunking %d neoplasm table entries", len(entries))

        chunks: list[ChunkData] = []
        for entry in entries:
            text = self._build_neoplasm_chunk_text(entry)
            chunk_key = f"neoplasm:{entry.term}:{entry.parent_term or ''}:{entry.level}"

            chunk = ChunkData(
                chunk_id=_generate_chunk_id("icd10cm_neoplasm", chunk_key),
                chunk_type="neoplasm_entry",
                text=text,
                metadata={
                    "term": entry.term,
                    "parent_term": entry.parent_term,
                    "level": entry.level,
                    "index_type": "neoplasm",
                    "matrix_codes": entry.matrix_codes,
                },
                code=None,
                standard_id=self.standard_id,
            )
            chunks.append(chunk)

        logger.info("Created %d neoplasm entry chunks", len(chunks))
        return chunks

    def _build_neoplasm_chunk_text(self, entry: IndexEntryData) -> str:
        """Build text representation for a neoplasm table entry."""
        lines: list[str] = []
        lines.append(f"Neoplasm Site: {entry.term}")

        if entry.parent_term:
            lines.append(f"Parent Site: {entry.parent_term}")

        if entry.see_reference:
            lines.append(f"See: {entry.see_reference}")

        if entry.see_also_reference:
            lines.append(f"See Also: {entry.see_also_reference}")

        if entry.matrix_codes:
            for col_name, code in entry.matrix_codes.items():
                lines.append(f"{col_name}: {code}")

        return "\n".join(lines)
