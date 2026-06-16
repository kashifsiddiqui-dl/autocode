"""CLI script to run the ICD-10-CM data ingestion pipeline.

Usage:
    python -m scripts.ingest_icd10cm \
        --data-dir data/ICD-10-CM/icd10cm-April-1-2026-XML \
        --database-url postgresql+asyncpg://user:pass@localhost:5432/autocode \
        --qdrant-url http://localhost:6333 \
        --openai-api-key sk-... \
        --batch-size 100

Flags:
    --skip-vectors     Skip Qdrant vector loading (useful for testing parsers)
    --skip-relational  Skip PostgreSQL relational loading
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time

from qdrant_client import QdrantClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.ingestion.pipeline import IngestionPipeline


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the ingestion pipeline."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Ingest ICD-10-CM data into AutoCode databases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--data-dir",
        required=True,
        help="Path to the ICD-10-CM XML data directory",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="PostgreSQL async connection string "
        "(e.g., postgresql+asyncpg://user:pass@localhost:5432/autocode)",
    )
    parser.add_argument(
        "--qdrant-url",
        default=None,
        help="Qdrant server URL (e.g., http://localhost:6333)",
    )
    parser.add_argument(
        "--openai-api-key",
        default=None,
        help="OpenAI API key for generating embeddings",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for embedding generation and vector loading (default: 100)",
    )
    parser.add_argument(
        "--skip-vectors",
        action="store_true",
        help="Skip Qdrant vector loading",
    )
    parser.add_argument(
        "--skip-relational",
        action="store_true",
        help="Skip PostgreSQL relational loading",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )

    return parser.parse_args()


async def main() -> None:
    """Main entry point for the ingestion CLI."""
    args = parse_args()
    setup_logging(args.verbose)

    logger = logging.getLogger(__name__)
    logger.info("ICD-10-CM Ingestion Pipeline")
    logger.info("Data directory: %s", args.data_dir)

    start_time = time.monotonic()

    # Set up database session if needed
    session: AsyncSession | None = None
    engine = None

    if not args.skip_relational:
        if not args.database_url:
            logger.error("--database-url is required unless --skip-relational is set")
            sys.exit(1)

        engine = create_async_engine(
            args.database_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
        )
        async_session_factory = sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        session = async_session_factory()

    # Set up Qdrant client if needed
    qdrant_client: QdrantClient | None = None
    if not args.skip_vectors:
        if not args.qdrant_url:
            logger.error("--qdrant-url is required unless --skip-vectors is set")
            sys.exit(1)
        if not args.openai_api_key:
            logger.error("--openai-api-key is required unless --skip-vectors is set")
            sys.exit(1)

        qdrant_client = QdrantClient(url=args.qdrant_url)

    # Create and run pipeline
    pipeline = IngestionPipeline(
        session=session,
        qdrant_client=qdrant_client,
        openai_api_key=args.openai_api_key,
        batch_size=args.batch_size,
        skip_vectors=args.skip_vectors,
        skip_relational=args.skip_relational,
    )

    try:
        stats = await pipeline.run(args.data_dir)
        elapsed = time.monotonic() - start_time
        logger.info("Pipeline completed in %.1f seconds", elapsed)
        logger.info("Final statistics: %s", stats)
    except Exception:
        logger.exception("Pipeline failed")
        sys.exit(1)
    finally:
        if session:
            await session.close()
        if engine:
            await engine.dispose()
        if qdrant_client:
            qdrant_client.close()


if __name__ == "__main__":
    asyncio.run(main())
