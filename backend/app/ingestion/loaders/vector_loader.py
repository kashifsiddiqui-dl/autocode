"""Vector database loader for ICD-10-CM chunks.

Handles embedding generation via OpenAI text-embedding-3-large and
batch upsertion into Qdrant with hybrid search support (dense + sparse).
"""

from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    NamedSparseVector,
    NamedVector,
    PayloadSchemaType,
    PointStruct,
    SparseIndexParams,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from app.rag.chunking.strategy import ChunkData

logger = logging.getLogger(__name__)

# Embedding configuration
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 1024
BATCH_SIZE = 100

# Collection names
CODES_COLLECTION = "icd10cm_codes"
INDEX_COLLECTION = "icd10cm_index"


def _simple_tokenize(text: str) -> dict[str, int]:
    """Simple whitespace tokenizer for BM25 sparse vectors.

    Produces a term frequency map suitable for sparse vector representation.
    In production, this should be replaced with a proper BM25 encoder
    (e.g., fastembed or SPLADE).
    """
    tokens: dict[str, int] = {}
    for word in text.lower().split():
        # Strip punctuation
        cleaned = word.strip(".,;:!?()[]{}\"'")
        if cleaned and len(cleaned) > 1:
            tokens[cleaned] = tokens.get(cleaned, 0) + 1
    return tokens


def _term_freqs_to_sparse_vector(term_freqs: dict[str, int]) -> SparseVector:
    """Convert term frequency dict to a Qdrant SparseVector.

    Uses hash of term as index (deterministic mapping).
    """
    indices: list[int] = []
    values: list[float] = []
    for term, freq in term_freqs.items():
        # Use hash modulo a large prime for index
        idx = hash(term) % 2_000_003
        indices.append(idx)
        values.append(float(freq))
    return SparseVector(indices=indices, values=values)


class VectorLoader:
    """Loads chunked ICD-10-CM data into Qdrant vector database.

    Supports hybrid search with:
    - Dense vectors from OpenAI text-embedding-3-large (1024 dimensions)
    - Sparse vectors for BM25-style keyword matching
    """

    def __init__(
        self,
        openai_api_key: str | None = None,
        batch_size: int = BATCH_SIZE,
    ) -> None:
        self._openai_client: OpenAI | None = None
        if openai_api_key:
            self._openai_client = OpenAI(api_key=openai_api_key)
        self.batch_size = batch_size

    def create_collections(self, client: QdrantClient) -> None:
        """Create Qdrant collections with proper vector configuration.

        Creates two collections:
        - icd10cm_codes: For billable diagnosis code chunks
        - icd10cm_index: For index entry chunks (disease, drug, neoplasm, eindex)

        Each collection has:
        - Named dense vector "description" (1024d, Cosine distance)
        - Named sparse vector "text_bm25" for keyword matching
        - Payload indexes on commonly filtered fields

        Args:
            client: Qdrant client instance.
        """
        for collection_name in [CODES_COLLECTION, INDEX_COLLECTION]:
            # Check if collection exists
            collections = client.get_collections().collections
            existing_names = {c.name for c in collections}

            if collection_name in existing_names:
                logger.info("Collection '%s' already exists, recreating", collection_name)
                client.delete_collection(collection_name)

            logger.info("Creating collection '%s'", collection_name)
            client.create_collection(
                collection_name=collection_name,
                vectors_config={
                    "description": VectorParams(
                        size=EMBEDDING_DIMENSIONS,
                        distance=Distance.COSINE,
                    ),
                },
                sparse_vectors_config={
                    "text_bm25": SparseVectorParams(
                        index=SparseIndexParams(on_disk=False),
                    ),
                },
            )

            # Create payload indexes for filtering
            client.create_payload_index(
                collection_name=collection_name,
                field_name="code",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            client.create_payload_index(
                collection_name=collection_name,
                field_name="is_billable",
                field_schema=PayloadSchemaType.BOOL,
            )
            client.create_payload_index(
                collection_name=collection_name,
                field_name="chapter_num",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            client.create_payload_index(
                collection_name=collection_name,
                field_name="section_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            client.create_payload_index(
                collection_name=collection_name,
                field_name="chunk_type",
                field_schema=PayloadSchemaType.KEYWORD,
            )

            logger.info("Collection '%s' created with indexes", collection_name)

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate dense embeddings using OpenAI text-embedding-3-large.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (each 1024 floats).

        Raises:
            RuntimeError: If OpenAI client is not configured.
        """
        if self._openai_client is None:
            raise RuntimeError(
                "OpenAI client not configured. Provide openai_api_key to VectorLoader."
            )

        embeddings: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            response = self._openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch,
                dimensions=EMBEDDING_DIMENSIONS,
            )
            batch_embeddings = [item.embedding for item in response.data]
            embeddings.extend(batch_embeddings)

            logger.info(
                "Generated embeddings: %d/%d",
                min(i + self.batch_size, len(texts)),
                len(texts),
            )

        return embeddings

    def load_chunks(
        self,
        client: QdrantClient,
        chunks: list[ChunkData],
        collection_name: str,
    ) -> int:
        """Batch upsert chunks into a Qdrant collection.

        For each chunk:
        1. Generates a dense embedding from the chunk text
        2. Creates a sparse BM25 vector from the chunk text
        3. Upserts the point with both vectors and full metadata payload

        Args:
            client: Qdrant client instance.
            chunks: List of ChunkData to load.
            collection_name: Target Qdrant collection name.

        Returns:
            Number of chunks loaded.
        """
        logger.info("Loading %d chunks into collection '%s'", len(chunks), collection_name)

        total_loaded = 0
        for batch_start in range(0, len(chunks), self.batch_size):
            batch = chunks[batch_start : batch_start + self.batch_size]

            # Generate dense embeddings for the batch
            texts = [chunk.text for chunk in batch]
            embeddings = self.generate_embeddings(texts)

            # Build Qdrant points
            points: list[PointStruct] = []
            for chunk, embedding in zip(batch, embeddings):
                # Generate sparse vector
                term_freqs = _simple_tokenize(chunk.text)
                sparse_vec = _term_freqs_to_sparse_vector(term_freqs)

                # Build payload from chunk metadata
                payload: dict[str, Any] = {
                    "chunk_id": chunk.chunk_id,
                    "chunk_type": chunk.chunk_type,
                    "text": chunk.text,
                    "standard_id": chunk.standard_id,
                }
                if chunk.code:
                    payload["code"] = chunk.code
                payload.update(chunk.metadata)

                point = PointStruct(
                    id=chunk.chunk_id,
                    vector={
                        "description": embedding,
                    },
                    payload=payload,
                )
                # Add sparse vector via named sparse vectors
                point.vector["text_bm25"] = sparse_vec  # type: ignore[assignment]
                points.append(point)

            client.upsert(
                collection_name=collection_name,
                points=points,
            )

            total_loaded += len(batch)
            logger.info(
                "Loaded chunks: %d/%d (%d%%)",
                total_loaded,
                len(chunks),
                int(total_loaded / len(chunks) * 100),
            )

        logger.info("Finished loading %d chunks into '%s'", total_loaded, collection_name)
        return total_loaded
