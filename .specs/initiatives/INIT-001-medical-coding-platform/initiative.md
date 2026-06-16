# INIT-001: Medical Coding Platform

## Status: In Progress
## Owner: kashif.siddiqui@disrupt.com
## Created: 2026-06-16

---

## SHAPE Framework

### Situation

Healthcare organizations face significant challenges with medical coding accuracy and efficiency. Manual ICD-10-CM coding is time-consuming, error-prone, and requires deep specialist knowledge. Coders must navigate 98,186 diagnosis codes across 22 chapters, each with complex hierarchies, excludes notes, and coding guidelines. Staff shortages, high turnover, and the constant evolution of coding standards compound the problem. Current software tools offer keyword lookup but lack contextual understanding of clinical narratives.

### Hypothesis

A RAG-based AI medical coding system grounded strictly in official ICD-10-CM data will outperform manual coding workflows in both accuracy and speed. By combining dense and sparse retrieval over chunked coding data, cross-encoder reranking, hierarchy-aware expansion, and LLM-driven analysis with post-validation against the source database, the system can deliver coding suggestions that are:

- More accurate than unaided manual coding (target: 95%+ top-5 accuracy)
- Faster than manual lookup (target: 80%+ time reduction per encounter)
- Fully traceable to official source material (zero hallucinated codes)

### Actions

1. **Data Ingestion Pipeline** -- Parse all 5 ICD-10-CM XML source files, load structured code data into PostgreSQL, generate embeddings, and load semantic chunks into Qdrant vector database.
2. **RAG Retrieval System** -- Build hybrid retrieval combining dense vector search and sparse keyword matching with metadata filtering, cross-encoder reranking, and hierarchy expansion.
3. **Coding API** -- Expose a streaming REST API that accepts clinical text, orchestrates the RAG pipeline, and returns validated coding suggestions with references.
4. **Web Interface** -- Build a responsive web UI for medical coders to input clinical notes, review AI-suggested codes, and manage coding sessions.
5. **Export System** -- Support PDF, CSV, JSON, and HL7 FHIR export of coded records with full audit trail.
6. **Code Browser** -- Provide a hierarchical browser for the ICD-10-CM codeset with semantic search.
7. **Multi-Tenant SaaS** -- Azure AD SSO, tenant isolation via RLS, role-based access control.
8. **EMR Integration** -- REST API with API key auth and webhook callbacks for EMR system integration.

### Plan

| Phase | Description | Duration | Features |
|-------|-------------|----------|----------|
| 1 | Foundation & Infrastructure | 1 week | Directory structure, Docker, DB schema, Qdrant |
| 2 | Data Ingestion | 1.5 weeks | FEAT-001: XML parsing, DB load, embeddings |
| 3 | RAG Pipeline | 1.5 weeks | FEAT-002: Retrieval, reranking, validation |
| 4 | Coding API | 1 week | FEAT-003: REST API, SSE streaming |
| 5 | Web Interface | 1.5 weeks | FEAT-004: Coding UI |
| 6 | Export & Browser | 1 week | FEAT-005: Export, FEAT-006: Code browser |
| 7 | Multi-Tenant & Auth | 1 week | FEAT-007: Auth, FEAT-008: Multi-standard |
| 8 | EMR Integration | 0.5 weeks | FEAT-009: EMR API |

**Total estimated duration: ~9 weeks**

### Evidence

Success will be measured by:

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Retrieval accuracy (top-10 recall) | >= 90% | Benchmark query set against known-correct codes |
| Coding accuracy (top-5) | >= 95% | Expert-reviewed clinical note test suite |
| Zero hallucination rate | 100% | Post-LLM validation against PostgreSQL code database |
| Time savings vs manual | >= 80% reduction | Timed coding sessions: AI-assisted vs manual |
| System latency (p95) | < 5 seconds | End-to-end from clinical text submission to results |
| Export correctness | 100% | Automated validation of exported records |

---

## Releases

- [R1: Foundation](releases/R1-foundation/release.md) -- Data ingestion, RAG pipeline, coding API
- [R2: Web Interface](releases/R2-web-interface/release.md) -- Web UI, export, code browser

## Standalone Features

- [FEAT-007: Multi-Tenant Auth](../../features/FEAT-007-multi-tenant-auth/spec.md)
- [FEAT-008: Multi-Standard Support](../../features/FEAT-008-multi-standard-support/spec.md)
- [FEAT-009: EMR Integration API](../../features/FEAT-009-emr-integration-api/spec.md)

## Supporting Documents

- [Journey Map](journey-map.md)
- [Architecture Runway](architecture/runway.md)
- [Dependency Graph](dependency-graph.md)
- [Parallel Tracks](parallel-tracks.md)
- [Progress Tracker](progress.md)
