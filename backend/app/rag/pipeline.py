"""RAG pipeline orchestrator: retrieve, rerank, expand, prompt, validate."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.icd_code import IcdCode
from app.rag.llm.base import BaseLLMProvider, LLMResponse
from app.rag.llm.prompts import (
    SYSTEM_PROMPT,
    build_user_prompt,
    format_retrieved_context,
)
from app.rag.reranker import CrossEncoderReranker
from app.rag.retriever import HybridRetriever, RetrievalResult

logger = logging.getLogger(__name__)


@dataclass
class CodeResult:
    code: str
    description: str
    confidence: str
    confidence_score: float
    rationale: str
    coding_instructions: str | None = None
    seventh_char: str | None = None
    source_chunk_id: str | None = None
    is_validated: bool = False
    validation_warning: str | None = None


@dataclass
class CodingOutput:
    codes: list[CodeResult] = field(default_factory=list)
    session_metadata: dict[str, Any] = field(default_factory=dict)
    validation_warnings: list[str] = field(default_factory=list)
    no_match_conditions: list[str] = field(default_factory=list)


class RAGPipeline:
    """Orchestrates the full 4-stage RAG pipeline for medical coding."""

    def __init__(
        self,
        retriever: HybridRetriever,
        reranker: CrossEncoderReranker,
        llm_provider: BaseLLMProvider,
        db_session: AsyncSession,
    ) -> None:
        self._retriever = retriever
        self._reranker = reranker
        self._llm = llm_provider
        self._db = db_session

    async def process_clinical_notes(
        self,
        clinical_text: str,
        standard_code: str = "icd10cm",
        options: dict[str, Any] | None = None,
    ) -> CodingOutput:
        """Run the full RAG pipeline and return validated coding results."""
        opts = options or {}
        timings: dict[str, float] = {}

        # Stage 1+2: Retrieve
        t0 = time.monotonic()
        retrieval_filters: dict[str, Any] = {}
        if opts.get("billable_only"):
            retrieval_filters["is_billable"] = True
        if opts.get("chapter_filter"):
            retrieval_filters["chapter_num"] = opts["chapter_filter"]

        candidates = await self._retriever.retrieve(
            query=clinical_text,
            top_k=opts.get("retrieval_top_k", 50),
            filters=retrieval_filters or None,
        )
        timings["retrieval_ms"] = (time.monotonic() - t0) * 1000

        # Stage 3: Rerank
        t0 = time.monotonic()
        reranked = self._reranker.rerank(
            query=clinical_text,
            results=candidates,
            top_k=opts.get("rerank_top_k", 10),
        )
        timings["reranking_ms"] = (time.monotonic() - t0) * 1000

        # Stage 4: Hierarchy expansion
        t0 = time.monotonic()
        codes_to_expand = [r.code for r in reranked if r.code]
        hierarchy = await self._expand_hierarchy(self._db, codes_to_expand)

        for r in reranked:
            if r.code in hierarchy:
                r.metadata.update(hierarchy[r.code])

        timings["hierarchy_ms"] = (time.monotonic() - t0) * 1000

        # Build prompt
        context_str = format_retrieved_context(reranked)
        user_prompt = build_user_prompt(context_str, clinical_text)

        # LLM call
        t0 = time.monotonic()
        llm_response = await self._llm.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=opts.get("max_tokens", 4096),
        )
        timings["llm_ms"] = (time.monotonic() - t0) * 1000

        # Parse LLM response
        parsed_codes = self._parse_llm_response(llm_response)

        # Validate against database
        t0 = time.monotonic()
        validated = await self._validate_codes(self._db, parsed_codes)
        timings["validation_ms"] = (time.monotonic() - t0) * 1000

        warnings = [c.validation_warning for c in validated if c.validation_warning]

        no_match = []
        try:
            raw = json.loads(llm_response.content)
            no_match = raw.get("no_match_conditions", [])
        except (json.JSONDecodeError, AttributeError):
            pass

        return CodingOutput(
            codes=validated,
            session_metadata={
                "timings": timings,
                "retrieval_count": len(candidates),
                "reranked_count": len(reranked),
                "llm_model": llm_response.model,
                "llm_usage": llm_response.usage,
                "llm_provider": self._llm.provider_name,
            },
            validation_warnings=warnings,
            no_match_conditions=no_match,
        )

    async def process_clinical_notes_stream(
        self,
        clinical_text: str,
        standard_code: str = "icd10cm",
        options: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Same as process_clinical_notes but yields SSE-compatible events."""
        opts = options or {}

        # Stage 1+2: Retrieve
        yield {"event": "stage", "data": {"stage": "retrieval", "status": "started"}}

        t0 = time.monotonic()
        retrieval_filters: dict[str, Any] = {}
        if opts.get("billable_only"):
            retrieval_filters["is_billable"] = True
        if opts.get("chapter_filter"):
            retrieval_filters["chapter_num"] = opts["chapter_filter"]

        candidates = await self._retriever.retrieve(
            query=clinical_text,
            top_k=opts.get("retrieval_top_k", 50),
            filters=retrieval_filters or None,
        )
        retrieval_ms = (time.monotonic() - t0) * 1000
        yield {
            "event": "stage",
            "data": {
                "stage": "retrieval",
                "status": "completed",
                "duration_ms": round(retrieval_ms),
                "candidates": len(candidates),
            },
        }

        # Stage 3: Rerank
        yield {"event": "stage", "data": {"stage": "reranking", "status": "started"}}

        t0 = time.monotonic()
        reranked = self._reranker.rerank(
            query=clinical_text,
            results=candidates,
            top_k=opts.get("rerank_top_k", 10),
        )
        reranking_ms = (time.monotonic() - t0) * 1000
        yield {
            "event": "stage",
            "data": {
                "stage": "reranking",
                "status": "completed",
                "duration_ms": round(reranking_ms),
                "candidates": len(reranked),
            },
        }

        # Stage 4: Hierarchy expansion
        codes_to_expand = [r.code for r in reranked if r.code]
        hierarchy = await self._expand_hierarchy(self._db, codes_to_expand)
        for r in reranked:
            if r.code in hierarchy:
                r.metadata.update(hierarchy[r.code])

        # LLM streaming
        yield {"event": "stage", "data": {"stage": "analysis", "status": "started"}}

        context_str = format_retrieved_context(reranked)
        user_prompt = build_user_prompt(context_str, clinical_text)

        t0 = time.monotonic()
        full_content = ""
        async for chunk in self._llm.generate_stream(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=opts.get("max_tokens", 4096),
        ):
            full_content += chunk
            yield {"event": "llm_chunk", "data": {"text": chunk}}

        llm_ms = (time.monotonic() - t0) * 1000

        # Parse and validate
        mock_response = LLMResponse(
            content=full_content,
            model=self._llm.model_name,
            usage={},
        )
        parsed_codes = self._parse_llm_response(mock_response)
        validated = await self._validate_codes(self._db, parsed_codes)

        for code_result in validated:
            yield {
                "event": "code",
                "data": {
                    "code": code_result.code,
                    "description": code_result.description,
                    "confidence": code_result.confidence,
                    "confidence_score": code_result.confidence_score,
                    "rationale": code_result.rationale,
                    "is_validated": code_result.is_validated,
                },
            }

        yield {
            "event": "stage",
            "data": {
                "stage": "validation",
                "status": "completed",
                "codes_validated": sum(1 for c in validated if c.is_validated),
                "codes_removed": sum(1 for c in validated if not c.is_validated),
            },
        }

        yield {
            "event": "complete",
            "data": {
                "total_codes": len(validated),
                "duration_ms": round(retrieval_ms + reranking_ms + llm_ms),
            },
        }

    async def _expand_hierarchy(
        self,
        session: AsyncSession,
        codes: list[str],
    ) -> dict[str, dict[str, Any]]:
        """For each code, fetch parent chain, sibling codes, and inherited notes."""
        if not codes:
            return {}

        result = await session.execute(
            select(IcdCode).where(IcdCode.code.in_(codes))
        )
        db_codes = {row.code: row for row in result.scalars().all()}

        hierarchy: dict[str, dict[str, Any]] = {}

        for code_str in codes:
            db_code = db_codes.get(code_str)
            if not db_code:
                continue

            entry: dict[str, Any] = {
                "is_billable": db_code.is_billable,
                "chapter_num": db_code.chapter_num,
                "chapter_name": db_code.chapter_name,
                "section_id": db_code.section_id,
                "section_name": db_code.section_name,
                "excludes1": db_code.excludes1,
                "excludes2": db_code.excludes2,
                "code_first": db_code.code_first,
                "use_additional_code": db_code.use_additional_code,
                "seven_chr_def": db_code.seven_chr_def,
            }

            # Fetch parent chain
            parents: list[dict[str, str]] = []
            parent_code = db_code.parent_code
            visited: set[str] = set()
            while parent_code and parent_code not in visited:
                visited.add(parent_code)
                parent_result = await session.execute(
                    select(IcdCode).where(IcdCode.code == parent_code)
                )
                parent_row = parent_result.scalar_one_or_none()
                if not parent_row:
                    break
                parents.append({
                    "code": parent_row.code,
                    "description": parent_row.description,
                })
                if parent_row.excludes1 and not entry.get("excludes1"):
                    entry["excludes1"] = parent_row.excludes1
                if parent_row.code_first and not entry.get("code_first"):
                    entry["code_first"] = parent_row.code_first
                parent_code = parent_row.parent_code

            entry["parents"] = parents

            # Fetch siblings
            if db_code.parent_code:
                sibling_result = await session.execute(
                    select(IcdCode.code, IcdCode.description, IcdCode.is_billable)
                    .where(IcdCode.parent_code == db_code.parent_code)
                    .where(IcdCode.code != code_str)
                    .limit(10)
                )
                entry["siblings"] = [
                    {"code": r.code, "description": r.description, "is_billable": r.is_billable}
                    for r in sibling_result.all()
                ]
            else:
                entry["siblings"] = []

            hierarchy[code_str] = entry

        return hierarchy

    async def _validate_codes(
        self,
        session: AsyncSession,
        codes: list[CodeResult],
    ) -> list[CodeResult]:
        """Check each code exists in the icd_codes table and flag hallucinated ones."""
        if not codes:
            return []

        code_strs = [c.code for c in codes]
        result = await session.execute(
            select(IcdCode).where(IcdCode.code.in_(code_strs))
        )
        valid_codes = {row.code: row for row in result.scalars().all()}

        validated: list[CodeResult] = []
        for code_result in codes:
            db_code = valid_codes.get(code_result.code)
            if db_code is None:
                code_result.is_validated = False
                code_result.validation_warning = (
                    f"Code {code_result.code} not found in database — possible hallucination"
                )
                logger.warning("Hallucinated code detected: %s", code_result.code)
            else:
                code_result.is_validated = True
                if not db_code.is_billable:
                    code_result.validation_warning = (
                        f"Code {code_result.code} is a category code (not billable). "
                        f"Consider a more specific child code."
                    )

            validated.append(code_result)

        return validated

    @staticmethod
    def _parse_llm_response(response: LLMResponse) -> list[CodeResult]:
        """Parse the LLM JSON response into CodeResult objects."""
        try:
            data = json.loads(response.content)
        except json.JSONDecodeError:
            content = response.content.strip()
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                try:
                    data = json.loads(content[json_start:json_end])
                except json.JSONDecodeError:
                    logger.error("Failed to parse LLM response as JSON")
                    return []
            else:
                logger.error("No JSON found in LLM response")
                return []

        raw_codes = data.get("codes", [])
        results: list[CodeResult] = []

        for entry in raw_codes:
            if not isinstance(entry, dict):
                continue
            code = entry.get("code", "").strip()
            if not code:
                continue

            results.append(
                CodeResult(
                    code=code,
                    description=entry.get("description", ""),
                    confidence=entry.get("confidence", "MEDIUM"),
                    confidence_score=float(entry.get("confidence_score", 0.5)),
                    rationale=entry.get("rationale", ""),
                    coding_instructions=entry.get("coding_instructions"),
                    seventh_char=entry.get("seventh_character"),
                    source_chunk_id=entry.get("source_chunk_id"),
                )
            )

        return results
