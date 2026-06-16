"""ICD-10-CM ingestion pipeline orchestrator.

Coordinates the full ingestion process: XML parsing, relational loading,
chunk generation, embedding creation, and vector database loading.
"""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID, uuid4

from qdrant_client import QdrantClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.loaders.relational_loader import RelationalLoader
from app.ingestion.loaders.vector_loader import (
    CODES_COLLECTION,
    INDEX_COLLECTION,
    VectorLoader,
)
from app.ingestion.parsers.drug import DrugParser
from app.ingestion.parsers.eindex import EIndexParser
from app.ingestion.parsers.index import IndexEntryData, IndexParser
from app.ingestion.parsers.neoplasm import NeoplasmParser
from app.ingestion.parsers.tabular import IcdCodeData, TabularParser
from app.rag.chunking.icd10cm import ICD10CMChunker

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """Orchestrates the full ICD-10-CM data ingestion process.

    Steps:
    1. Parse all XML files (tabular, disease index, drug table,
       neoplasm table, external causes index)
    2. Create/get coding standard record in PostgreSQL
    3. Load codes and index entries into PostgreSQL
    4. Generate text chunks for vector search
    5. Generate embeddings via OpenAI
    6. Load chunks into Qdrant
    7. Validate counts
    """

    def __init__(
        self,
        session: AsyncSession | None = None,
        qdrant_client: QdrantClient | None = None,
        openai_api_key: str | None = None,
        batch_size: int = 100,
        skip_vectors: bool = False,
        skip_relational: bool = False,
    ) -> None:
        self.session = session
        self.qdrant_client = qdrant_client
        self.skip_vectors = skip_vectors
        self.skip_relational = skip_relational

        self.tabular_parser = TabularParser()
        self.index_parser = IndexParser()
        self.drug_parser = DrugParser()
        self.neoplasm_parser = NeoplasmParser()
        self.eindex_parser = EIndexParser()

        self.relational_loader = RelationalLoader()
        self.vector_loader = VectorLoader(
            openai_api_key=openai_api_key,
            batch_size=batch_size,
        )
        self.chunker = ICD10CMChunker()

    async def run(
        self,
        data_dir: str,
        standard_code: str = "icd10cm",
    ) -> dict[str, int]:
        """Run the full ingestion pipeline.

        Args:
            data_dir: Path to the ICD-10-CM data directory containing XML files.
            standard_code: Coding standard identifier (default: "icd10cm").

        Returns:
            Dictionary with counts of processed items.
        """
        data_path = Path(data_dir)
        logger.info("Starting ICD-10-CM ingestion from: %s", data_path)

        stats: dict[str, int] = {}

        # ── Step 1: Parse all XML files ──────────────────────────────────
        logger.info("Step 1: Parsing XML files")

        codes = self._parse_tabular(data_path)
        stats["codes_parsed"] = len(codes)

        disease_entries = self._parse_disease_index(data_path)
        stats["disease_entries_parsed"] = len(disease_entries)

        drug_entries = self._parse_drug_table(data_path)
        stats["drug_entries_parsed"] = len(drug_entries)

        neoplasm_entries = self._parse_neoplasm_table(data_path)
        stats["neoplasm_entries_parsed"] = len(neoplasm_entries)

        eindex_entries = self._parse_eindex(data_path)
        stats["eindex_entries_parsed"] = len(eindex_entries)

        total_parsed = sum(stats.values())
        logger.info("Parsing complete. Total items parsed: %d", total_parsed)

        # ── Step 2 & 3: Relational loading ───────────────────────────────
        if not self.skip_relational:
            if self.session is None:
                logger.error("Database session required for relational loading")
                raise RuntimeError("Database session not provided")

            logger.info("Step 2: Getting/creating coding standard record")
            standard_id = await self._get_or_create_standard(
                self.session, standard_code
            )

            logger.info("Step 3: Loading data into PostgreSQL")
            try:
                stats["codes_loaded"] = await self.relational_loader.load_codes(
                    self.session, codes, standard_id
                )

                all_index_entries = (
                    disease_entries + drug_entries + neoplasm_entries + eindex_entries
                )
                stats["index_entries_loaded"] = (
                    await self.relational_loader.load_index_entries(
                        self.session, all_index_entries, standard_id
                    )
                )
                logger.info("Relational loading complete")
            except Exception:
                logger.exception("Error during relational loading")
                raise
        else:
            logger.info("Skipping relational loading (--skip-relational)")

        # ── Step 4: Generate chunks ──────────────────────────────────────
        logger.info("Step 4: Generating text chunks")

        code_chunks = self.chunker.chunk_codes(codes)
        stats["code_chunks"] = len(code_chunks)

        disease_chunks = self.chunker.chunk_index_entries(disease_entries)
        stats["disease_index_chunks"] = len(disease_chunks)

        drug_chunks = self.chunker.chunk_drug_entries(drug_entries)
        stats["drug_chunks"] = len(drug_chunks)

        neoplasm_chunks = self.chunker.chunk_neoplasm_entries(neoplasm_entries)
        stats["neoplasm_chunks"] = len(neoplasm_chunks)

        eindex_chunks = self.chunker.chunk_index_entries(eindex_entries)
        stats["eindex_chunks"] = len(eindex_chunks)

        logger.info(
            "Chunk generation complete: %d code chunks, %d index chunks",
            stats["code_chunks"],
            stats["disease_index_chunks"]
            + stats["drug_chunks"]
            + stats["neoplasm_chunks"]
            + stats["eindex_chunks"],
        )

        # ── Step 5 & 6: Vector loading ───────────────────────────────────
        if not self.skip_vectors:
            if self.qdrant_client is None:
                logger.error("Qdrant client required for vector loading")
                raise RuntimeError("Qdrant client not provided")

            logger.info("Step 5: Creating Qdrant collections")
            self.vector_loader.create_collections(self.qdrant_client)

            logger.info("Step 6: Generating embeddings and loading into Qdrant")
            try:
                stats["code_vectors_loaded"] = self.vector_loader.load_chunks(
                    self.qdrant_client, code_chunks, CODES_COLLECTION
                )

                all_index_chunks = (
                    disease_chunks + drug_chunks + neoplasm_chunks + eindex_chunks
                )
                stats["index_vectors_loaded"] = self.vector_loader.load_chunks(
                    self.qdrant_client, all_index_chunks, INDEX_COLLECTION
                )

                logger.info("Vector loading complete")
            except Exception:
                logger.exception("Error during vector loading")
                raise
        else:
            logger.info("Skipping vector loading (--skip-vectors)")

        # ── Step 7: Validate ─────────────────────────────────────────────
        logger.info("Step 7: Validation")
        self._log_stats(stats)

        logger.info("ICD-10-CM ingestion pipeline complete")
        return stats

    def _parse_tabular(self, data_path: Path) -> list[IcdCodeData]:
        """Find and parse the tabular XML file."""
        # The tabular file has a typo in the name: "icd10c-tabular" not "icd10cm-tabular"
        candidates = [
            data_path / "icd10c-tabular-April-1-2026.xml",
            data_path / "icd10cm-tabular-April-1-2026.xml",
        ]
        for candidate in candidates:
            if candidate.exists():
                return self.tabular_parser.parse(candidate)

        # Try glob pattern
        matches = list(data_path.glob("*tabular*.xml"))
        if matches:
            return self.tabular_parser.parse(matches[0])

        logger.warning("Tabular XML file not found in %s", data_path)
        return []

    def _parse_disease_index(self, data_path: Path) -> list[IndexEntryData]:
        """Find and parse the disease index XML file."""
        candidates = [
            data_path / "icd10cm-index-April-1-2026-XML.xml",
        ]
        for candidate in candidates:
            if candidate.exists():
                return self.index_parser.parse(candidate)

        matches = list(data_path.glob("*index*XML.xml"))
        # Exclude drug, neoplasm, eindex
        for m in matches:
            name = m.name.lower()
            if "drug" not in name and "neoplasm" not in name and "eindex" not in name:
                return self.index_parser.parse(m)

        logger.warning("Disease index XML file not found in %s", data_path)
        return []

    def _parse_drug_table(self, data_path: Path) -> list[IndexEntryData]:
        """Find and parse the drug table XML file."""
        candidates = [
            data_path / "icd10cm-drug-April-1-2026-XML.xml",
        ]
        for candidate in candidates:
            if candidate.exists():
                return self.drug_parser.parse(candidate)

        matches = list(data_path.glob("*drug*XML.xml"))
        if matches:
            return self.drug_parser.parse(matches[0])

        logger.warning("Drug table XML file not found in %s", data_path)
        return []

    def _parse_neoplasm_table(self, data_path: Path) -> list[IndexEntryData]:
        """Find and parse the neoplasm table XML file."""
        candidates = [
            data_path / "icd10cm-neoplasm-April-1-2026-XML.xml",
        ]
        for candidate in candidates:
            if candidate.exists():
                return self.neoplasm_parser.parse(candidate)

        matches = list(data_path.glob("*neoplasm*XML.xml"))
        if matches:
            return self.neoplasm_parser.parse(matches[0])

        logger.warning("Neoplasm table XML file not found in %s", data_path)
        return []

    def _parse_eindex(self, data_path: Path) -> list[IndexEntryData]:
        """Find and parse the external causes index XML file."""
        candidates = [
            data_path / "icd10cm-eindex-April-1-2026-XML.xml",
        ]
        for candidate in candidates:
            if candidate.exists():
                return self.eindex_parser.parse(candidate)

        matches = list(data_path.glob("*eindex*XML.xml"))
        if matches:
            return self.eindex_parser.parse(matches[0])

        logger.warning("External causes index XML file not found in %s", data_path)
        return []

    async def _get_or_create_standard(
        self,
        session: AsyncSession,
        standard_code: str,
    ) -> UUID:
        """Get or create a coding standard record in PostgreSQL.

        Args:
            session: Database session.
            standard_code: Standard identifier (e.g., "icd10cm").

        Returns:
            UUID of the coding standard record.
        """
        # Try to find existing standard
        result = await session.execute(
            text("SELECT id FROM coding_standards WHERE code = :code"),
            {"code": standard_code},
        )
        row = result.fetchone()
        if row:
            standard_id = UUID(str(row[0]))
            logger.info("Found existing coding standard: %s (id=%s)", standard_code, standard_id)
            return standard_id

        # Create new standard
        standard_id = uuid4()
        await session.execute(
            text("""
                INSERT INTO coding_standards (id, code, name, version)
                VALUES (:id::uuid, :code, :name, :version)
            """),
            {
                "id": str(standard_id),
                "code": standard_code,
                "name": "ICD-10-CM",
                "version": "2026",
            },
        )
        await session.commit()
        logger.info("Created coding standard: %s (id=%s)", standard_code, standard_id)
        return standard_id

    def _log_stats(self, stats: dict[str, int]) -> None:
        """Log pipeline statistics."""
        logger.info("=" * 60)
        logger.info("INGESTION PIPELINE STATISTICS")
        logger.info("=" * 60)
        for key, value in stats.items():
            logger.info("  %-30s %d", key, value)
        logger.info("=" * 60)
