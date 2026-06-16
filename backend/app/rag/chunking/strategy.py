"""Abstract base class for chunking strategies.

Defines the interface and data structures for converting parsed medical coding
data into text chunks suitable for vector embedding and retrieval.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChunkData:
    """A single chunk of text ready for embedding and vector storage."""

    chunk_id: str
    chunk_type: str  # e.g. "code", "index_entry", "drug_entry", "neoplasm_entry"
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    code: str | None = None  # ICD-10 code if applicable
    standard_id: str = ""  # e.g. "icd10cm"


class ChunkingStrategy(ABC):
    """Abstract base class for domain-specific chunking strategies.

    Each coding standard (ICD-10-CM, CPT, HCPCS, etc.) implements its own
    chunking strategy to produce semantically rich text chunks optimized
    for retrieval-augmented generation.
    """

    @abstractmethod
    def chunk(self, data: Any) -> list[ChunkData]:
        """Convert parsed data into a list of text chunks.

        Args:
            data: Parsed data from a coding standard parser.

        Returns:
            List of ChunkData objects ready for embedding.
        """
        ...
