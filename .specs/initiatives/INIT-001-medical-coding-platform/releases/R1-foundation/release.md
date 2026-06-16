# Release 1: Foundation

## Initiative: INIT-001 Medical Coding Platform
## Status: Not Started
## Target Date: TBD
## Owner: kashif.siddiqui@disrupt.com

---

## Scope

Release 1 establishes the core data pipeline and AI coding engine. Upon completion, the system can ingest ICD-10-CM source data, perform RAG-based retrieval over clinical text, and expose a streaming API for coding analysis.

## Goals

1. Ingest all 5 ICD-10-CM XML source files into PostgreSQL and Qdrant
2. Build a production-quality RAG pipeline with hybrid retrieval and reranking
3. Expose a REST API with SSE streaming for real-time coding suggestions
4. Achieve 90%+ retrieval accuracy on benchmark queries

## Features

| Feature | Name | Priority | Status |
|---------|------|----------|--------|
| [FEAT-001](features/FEAT-001-data-ingestion/spec.md) | Data Ingestion Pipeline | P0 | Not Started |
| [FEAT-002](features/FEAT-002-rag-pipeline/spec.md) | RAG Pipeline | P0 | Not Started |
| [FEAT-003](features/FEAT-003-coding-api/spec.md) | Coding API | P0 | Not Started |

## Dependencies

- Architecture runway must be complete (Docker, DB schema, Qdrant setup)
- ICD-10-CM April 2026 XML source files available in `data/ICD-10-CM/`
- OpenAI API key for embeddings (text-embedding-3-small)
- Anthropic API key for LLM analysis (Claude)

## Success Criteria

| Criterion | Target | Validation |
|-----------|--------|------------|
| Data completeness | 98,186 codes loaded | Count query against codes table |
| Vector completeness | ~130K chunks in Qdrant | Collection info query |
| Retrieval accuracy | >= 90% top-10 recall | Benchmark query set (50+ queries) |
| Zero hallucination | 100% codes validated | Post-LLM validation against DB |
| API response time | < 5s p95 | Load test with representative queries |
| API availability | SSE streaming works | End-to-end integration test |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| XML parsing edge cases | Data gaps | Comprehensive validation step post-ingestion |
| Embedding quality | Poor retrieval | Test multiple embedding models, tune chunk strategy |
| LLM latency | Slow user experience | SSE streaming, response caching for repeated queries |
| Qdrant performance at scale | Slow retrieval | Index optimization, HNSW parameter tuning |

## Release Checklist

- [ ] All FEAT-001 acceptance criteria met
- [ ] All FEAT-002 acceptance criteria met
- [ ] All FEAT-003 acceptance criteria met
- [ ] Integration tests passing
- [ ] Benchmark suite run and results documented
- [ ] Performance baseline established
- [ ] API documentation generated
