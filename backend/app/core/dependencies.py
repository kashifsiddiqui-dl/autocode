"""FastAPI dependency injection providers."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_session
from app.db.vector import qdrant_manager
from app.rag.embeddings import EmbeddingService
from app.rag.llm.factory import LLMFactory
from app.rag.reranker import CrossEncoderReranker
from app.rag.retriever import HybridRetriever


@dataclass
class CurrentUser:
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    role: str


async def get_current_user(request: Request) -> CurrentUser:
    """Extract the authenticated user from the request.

    In development, reads from headers injected by the auth middleware.
    In production, the auth middleware validates the JWT and populates request.state.
    """
    user = getattr(request.state, "user", None)
    if user is not None:
        return user

    user_id = request.headers.get("x-user-id")
    tenant_id = request.headers.get("x-tenant-id")
    email = request.headers.get("x-user-email", "dev@localhost")
    role = request.headers.get("x-user-role", "coder")

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    return CurrentUser(
        id=uuid.UUID(user_id),
        tenant_id=uuid.UUID(tenant_id),
        email=email,
        role=role,
    )


def require_role(*roles: str):
    """Return a dependency that enforces one of the given roles."""

    async def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(roles)}",
            )
        return user

    return _checker


async def get_db(
    request: Request,
) -> AsyncGenerator[AsyncSession, None]:
    """Yield a tenant-scoped database session."""
    async for session in get_session():
        user = getattr(request.state, "user", None)
        if user is not None:
            await session.execute(
                __import__("sqlalchemy").text(
                    f"SET LOCAL app.current_tenant_id = '{user.tenant_id}'"
                )
            )
        yield session


def get_qdrant_client():
    return qdrant_manager.get_client()


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(
        api_key=settings.OPENAI_API_KEY,
        model=settings.EMBEDDING_MODEL,
        dimensions=settings.EMBEDDING_DIMENSIONS,
    )


def get_retriever(
    qdrant_client=Depends(get_qdrant_client),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> HybridRetriever:
    return HybridRetriever(
        qdrant_client=qdrant_client,
        embedding_service=embedding_service,
        collection_name="icd10cm_codes",
    )


_reranker: CrossEncoderReranker | None = None


def get_reranker() -> CrossEncoderReranker:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoderReranker()
    return _reranker


def get_llm_provider(provider: str | None = None, model: str | None = None):
    return LLMFactory.create(
        provider=provider or settings.LLM_PROVIDER,
        api_key=(
            settings.ANTHROPIC_API_KEY
            if (provider or settings.LLM_PROVIDER) == "anthropic"
            else settings.OPENAI_API_KEY
        ),
        model=model or settings.LLM_MODEL,
    )


DBSession = Annotated[AsyncSession, Depends(get_db)]
AuthUser = Annotated[CurrentUser, Depends(get_current_user)]
AdminUser = Annotated[CurrentUser, Depends(require_role("admin"))]
