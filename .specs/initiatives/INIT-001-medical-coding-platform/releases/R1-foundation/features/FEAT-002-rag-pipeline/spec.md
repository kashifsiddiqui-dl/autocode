# FEAT-002: RAG Pipeline

## Status: Not Started
## Priority: P0
## Release: R1 Foundation
## Owner: TBD
## Estimated Effort: 1.5 weeks
## Depends On: FEAT-001

---

## Summary

Build a Retrieval-Augmented Generation pipeline that combines hybrid retrieval (dense vector + sparse keyword search), metadata filtering, cross-encoder reranking, hierarchy expansion, negative prompting, and post-LLM validation to produce accurate, hallucination-free ICD-10-CM coding suggestions from clinical text.

## Problem Statement

Clinical notes are written in natural language with medical terminology, abbreviations, and contextual nuances. A single retrieval approach (pure vector search or pure keyword search) is insufficient to reliably map clinical text to the correct ICD-10-CM codes. The system must combine multiple retrieval strategies, intelligently rerank results, expand hierarchical context, and validate all outputs against the source database to ensure zero hallucinated codes.

## Functional Requirements

### FR-1: Query Processing

- Accept raw clinical text input (up to 10,000 characters)
- Extract key clinical terms and conditions using NLP preprocessing
- Generate query embedding using the same model as ingestion (text-embedding-3-small)
- Support optional metadata filters (chapter, code_type, billable_only)

### FR-2: Dense Retrieval

- Perform vector similarity search on Qdrant `icd10cm_chunks` collection
- Use cosine similarity with configurable top-K (default: 50)
- Apply metadata filters to narrow search scope when provided
- Return scored results with full payload metadata

### FR-3: Sparse Retrieval

- Perform keyword-based search using PostgreSQL full-text search
- Build tsvector index on `codes.description` and `codes.long_description`
- Use `ts_rank_cd` for relevance scoring
- Return top-K results (default: 30) with scores normalized to 0-1 range

### FR-4: Hybrid Fusion

- Combine dense and sparse retrieval results using Reciprocal Rank Fusion (RRF)
- RRF formula: `score = sum(1 / (k + rank_i))` where k=60 (constant)
- Deduplicate results by code (keep highest-scoring occurrence)
- Output fused candidate set of top-N codes (default: 30)

### FR-5: Cross-Encoder Reranking

- Apply cross-encoder model (ms-marco-MiniLM-L-12-v2) to rerank candidates
- Input pairs: (clinical_text, chunk_content) for each candidate
- Batch processing for efficiency (batch size: 16)
- Output reranked list sorted by cross-encoder score
- Take top-M results post-reranking (default: 15)

### FR-6: Hierarchy Expansion

For each reranked code:
- Fetch parent codes up to the chapter level from PostgreSQL
- Fetch sibling codes at the same level
- Fetch any child codes (more specific alternatives)
- Include Excludes1 notes (mutually exclusive codes -- cannot be coded together)
- Include Excludes2 notes (not included here, code additionally if applicable)
- Include "Code first" and "Use additional code" annotations
- Build complete hierarchy context for LLM analysis

### FR-7: LLM Analysis with Negative Prompting

System prompt structure:

```
You are a medical coding assistant. Analyze the clinical text and determine
which ICD-10-CM codes from the candidate set are applicable.

RULES:
1. ONLY suggest codes from the provided candidate set
2. NEVER invent or suggest codes not in the candidate set
3. For each suggested code, explain WHY it applies to the clinical text
4. Consider excludes notes -- do not suggest mutually exclusive codes together
5. Prefer the most specific (billable) code available
6. Consider "Code first" and "Use additional code" instructions
7. If the clinical text does not support a code, explicitly REJECT it
8. Rate your confidence for each code (0.0 to 1.0)

NEGATIVE EXAMPLES (do NOT do this):
- Do not suggest codes for conditions not mentioned in the clinical text
- Do not suggest parent codes when a more specific child code applies
- Do not suggest both a code and its Excludes1 counterpart
- Do not guess -- if uncertain, lower the confidence score
```

Input to LLM:
- Clinical text
- Candidate codes with hierarchy context, descriptions, and notes
- Specific instructions for code selection

Output from LLM:
- List of suggested codes with confidence scores and reasoning
- Explicit rejections for non-applicable candidates

### FR-8: Post-LLM Validation

Every code suggested by the LLM must pass validation:

1. **Existence check**: Verify code exists in PostgreSQL `codes` table
2. **Billability check**: Flag non-billable codes (parent codes that should be more specific)
3. **Excludes check**: Detect and warn about Excludes1 conflicts in the suggested set
4. **Format check**: Verify code format matches ICD-10-CM pattern (letter + 2-7 characters)
5. **Active check**: Verify code belongs to the active coding standard version

Any code failing validation is removed from results with a logged warning.

### FR-9: Response Assembly

Assemble the final response:

```python
@dataclass
class CodingSuggestion:
    code: str                    # e.g., "E11.9"
    description: str             # "Type 2 diabetes mellitus without complications"
    confidence: float            # 0.0 - 1.0
    reasoning: str               # LLM's explanation
    hierarchy: HierarchyPath     # Chapter > Section > Category > Code
    excludes1: list[str]         # Mutually exclusive codes
    excludes2: list[str]         # Additional codes to consider
    annotations: list[str]       # Code-first, use-additional notes
    source_chunks: list[str]     # Qdrant chunk IDs used as evidence
    is_billable: bool            # Whether code is billable
```

## Non-Functional Requirements

- **Latency**: Full pipeline from clinical text to results in < 5 seconds (p95)
- **Accuracy**: >= 90% top-10 recall on benchmark query set
- **Zero hallucination**: 100% of suggested codes must exist in the database
- **Determinism**: Same input should produce consistent (though not necessarily identical) results
- **Observability**: Log timing for each pipeline stage (retrieval, reranking, LLM, validation)

## Technical Design

### Pipeline Architecture

```
Clinical Text
      |
      v
[Query Processor] -- term extraction, embedding generation
      |
      +---> [Dense Retrieval] -- Qdrant vector search (top-50)
      |           |
      +---> [Sparse Retrieval] -- PostgreSQL FTS (top-30)
      |           |
      v           v
[Hybrid Fusion] -- RRF merge + dedup (top-30)
      |
      v
[Cross-Encoder Reranking] -- ms-marco-MiniLM-L-12-v2 (top-15)
      |
      v
[Hierarchy Expansion] -- parent/child/sibling codes, excludes, notes
      |
      v
[LLM Analysis] -- Claude with negative prompting
      |
      v
[Post-LLM Validation] -- existence, billability, excludes conflicts
      |
      v
[Response Assembly] -- structured CodingSuggestion objects
```

### Configuration

```python
class RAGConfig:
    # Retrieval
    dense_top_k: int = 50
    sparse_top_k: int = 30
    fusion_top_n: int = 30
    rrf_k: int = 60

    # Reranking
    rerank_top_m: int = 15
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-12-v2"
    rerank_batch_size: int = 16

    # LLM
    llm_model: str = "claude-sonnet-4-20250514"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.0   # Deterministic for coding

    # Validation
    min_confidence_threshold: float = 0.3
    max_suggestions: int = 10
```

## Acceptance Criteria

- [ ] Dense retrieval returns relevant results for clinical text queries
- [ ] Sparse retrieval returns relevant results for keyword-heavy queries
- [ ] Hybrid fusion improves recall over either method alone (measured on benchmark set)
- [ ] Cross-encoder reranking improves precision in top-5 results
- [ ] Hierarchy expansion includes parent codes, excludes notes, and annotations
- [ ] LLM analysis produces structured output with codes, confidence, and reasoning
- [ ] Negative prompting prevents hallucinated codes in LLM output
- [ ] Post-validation catches and removes any codes not in the database
- [ ] Pipeline achieves >= 90% top-10 recall on benchmark queries
- [ ] End-to-end latency < 5 seconds (p95) for typical clinical notes
- [ ] All pipeline stages emit timing metrics

## Test Plan

### Unit Tests
- Test query processor term extraction
- Test RRF fusion algorithm with known inputs
- Test post-validation logic (existence, billability, excludes)
- Test response assembly

### Integration Tests
- Test dense retrieval against Qdrant with real data
- Test sparse retrieval against PostgreSQL with real data
- Test full pipeline end-to-end with sample clinical notes

### Benchmark Tests
- Create benchmark set of 50+ clinical notes with known-correct codes
- Measure top-1, top-5, top-10 recall
- Measure precision at different confidence thresholds
- Measure end-to-end latency distribution

### Negative Tests
- Submit nonsensical text -- should return empty or very low confidence results
- Submit text mentioning conditions not in ICD-10-CM -- should not hallucinate codes
- Submit text that maps to mutually exclusive codes -- should handle Excludes1 correctly
