"""Code browsing and search endpoints."""

from __future__ import annotations

import logging
import math
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import AuthUser, DBSession, get_embedding_service, get_qdrant_client
from app.core.exceptions import NotFoundError
from app.models.icd_code import IcdCode
from app.rag.embeddings import EmbeddingService
from app.schemas.codes import (
    CodeHierarchyResponse,
    CodeResponse,
    CodeSearchParams,
    CodeSummary,
    HierarchyNode,
    SemanticSearchResult,
)
from app.schemas.common import PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=PaginatedResponse[CodeSummary])
async def list_codes(
    user: AuthUser,
    db: DBSession,
    q: str | None = Query(default=None, min_length=2, max_length=200),
    chapter: int | None = Query(default=None),
    billable: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
):
    """Browse codes with optional filters and text search."""
    base = select(IcdCode)

    if q is not None:
        like = f"%{q}%"
        base = base.where(
            IcdCode.code.ilike(like) | IcdCode.description.ilike(like)
        )
    if chapter is not None:
        base = base.where(IcdCode.chapter_num == chapter)
    if billable is not None:
        base = base.where(IcdCode.is_billable == billable)

    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * size
    rows_stmt = base.order_by(IcdCode.code).offset(offset).limit(size)
    result = await db.execute(rows_stmt)
    codes = result.scalars().all()

    return PaginatedResponse(
        items=[CodeSummary.model_validate(c) for c in codes],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if size else 0,
    )


@router.get("/search", response_model=list[SemanticSearchResult])
async def semantic_search(
    user: AuthUser,
    q: str = Query(..., min_length=2, max_length=500),
    limit: int = Query(default=20, ge=1, le=100),
    qdrant_client=Depends(get_qdrant_client),
    embedding_svc: EmbeddingService = Depends(get_embedding_service),
):
    """Semantic search for codes via the vector database."""
    query_vector = await embedding_svc.embed_query(q)

    try:
        hits = await qdrant_client.search(
            collection_name="icd10cm_codes",
            query_vector=("description", query_vector),
            limit=limit,
            with_payload=True,
        )
    except Exception:
        hits = await qdrant_client.search(
            collection_name="icd10cm_codes",
            query_vector=query_vector,
            limit=limit,
            with_payload=True,
        )

    results: list[SemanticSearchResult] = []
    seen: set[str] = set()
    for hit in hits:
        payload = hit.payload or {}
        code = payload.get("code", "")
        if code in seen:
            continue
        seen.add(code)
        results.append(
            SemanticSearchResult(
                code=code,
                description=payload.get("description", ""),
                is_billable=payload.get("is_billable", False),
                score=hit.score,
                chapter_num=payload.get("chapter_num"),
            )
        )

    return results


@router.get("/{code}", response_model=CodeResponse)
async def get_code(
    code: str,
    user: AuthUser,
    db: DBSession,
):
    """Get full details for a single ICD-10-CM code."""
    result = await db.execute(select(IcdCode).where(IcdCode.code == code))
    db_code = result.scalar_one_or_none()
    if db_code is None:
        raise NotFoundError(f"Code '{code}' not found")
    return CodeResponse.model_validate(db_code)


@router.get("/{code}/hierarchy", response_model=CodeHierarchyResponse)
async def get_hierarchy(
    code: str,
    user: AuthUser,
    db: DBSession,
):
    """Get the hierarchy for a code: parent chain, siblings, and children."""
    result = await db.execute(select(IcdCode).where(IcdCode.code == code))
    db_code = result.scalar_one_or_none()
    if db_code is None:
        raise NotFoundError(f"Code '{code}' not found")

    # Parents
    parents: list[HierarchyNode] = []
    parent_code = db_code.parent_code
    visited: set[str] = set()
    while parent_code and parent_code not in visited:
        visited.add(parent_code)
        p_result = await db.execute(select(IcdCode).where(IcdCode.code == parent_code))
        parent = p_result.scalar_one_or_none()
        if parent is None:
            break
        parents.append(
            HierarchyNode(
                code=parent.code,
                description=parent.description,
                is_billable=parent.is_billable,
                level=parent.code_level,
            )
        )
        parent_code = parent.parent_code

    # Siblings
    siblings: list[HierarchyNode] = []
    if db_code.parent_code:
        sib_result = await db.execute(
            select(IcdCode)
            .where(IcdCode.parent_code == db_code.parent_code, IcdCode.code != code)
            .order_by(IcdCode.code)
            .limit(20)
        )
        for sib in sib_result.scalars().all():
            siblings.append(
                HierarchyNode(
                    code=sib.code,
                    description=sib.description,
                    is_billable=sib.is_billable,
                    level=sib.code_level,
                )
            )

    # Children
    children: list[HierarchyNode] = []
    child_result = await db.execute(
        select(IcdCode)
        .where(IcdCode.parent_code == code)
        .order_by(IcdCode.code)
        .limit(50)
    )
    for child in child_result.scalars().all():
        children.append(
            HierarchyNode(
                code=child.code,
                description=child.description,
                is_billable=child.is_billable,
                level=child.code_level,
            )
        )

    return CodeHierarchyResponse(
        code=db_code.code,
        description=db_code.description,
        parents=parents,
        siblings=siblings,
        children=children,
    )
