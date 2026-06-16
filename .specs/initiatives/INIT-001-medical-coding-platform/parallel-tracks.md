# Parallel Tracks: Team/Agent Assignment

## Initiative: INIT-001 Medical Coding Platform
## Last Updated: 2026-06-16

---

## Parallel Execution Strategy

The dependency graph allows up to 3 parallel tracks of work. This document maps features to tracks and identifies optimal sequencing for maximum parallelism.

---

## Track Assignments

### Track A: Data & AI Pipeline (Backend - AI/ML Focus)

**Focus:** Data ingestion, RAG pipeline, and coding intelligence
**Skills Required:** Python, XML parsing, embeddings, vector databases, LLM orchestration

| Week | Feature | Tasks |
|------|---------|-------|
| 1 | Architecture Runway | Docker setup, DB schema, Qdrant config |
| 2-3 | FEAT-001: Data Ingestion | XML parsers, PostgreSQL loading, embeddings, Qdrant loading |
| 3-4 | FEAT-002: RAG Pipeline | Hybrid retrieval, reranking, LLM analysis, validation |
| 5 | FEAT-008: Multi-Standard | Parser interface, standard registry, standard-aware routing |
| 6-7 | Benchmarking & Optimization | Retrieval accuracy tuning, latency optimization |

### Track B: API & Integration (Backend - API Focus)

**Focus:** REST API, SSE streaming, auth, EMR integration
**Skills Required:** Python, FastAPI, SSE, JWT/OIDC, HL7 FHIR

| Week | Feature | Tasks |
|------|---------|-------|
| 1-2 | FEAT-007: Multi-Tenant Auth | Azure AD OIDC, JWT, RLS, RBAC |
| 3-4 | FEAT-003: Coding API | REST endpoints, SSE streaming, session management |
| 5 | FEAT-005: Export (Backend) | Export generators (PDF, CSV, JSON, FHIR) |
| 6 | FEAT-009: EMR Integration | API key auth, webhooks, FHIR input/output |
| 7 | API Documentation & Testing | OpenAPI docs, contract tests, load tests |

### Track C: Frontend (Web UI)

**Focus:** Web interface, code browser, export UI
**Skills Required:** TypeScript, React, Next.js, SSE client, UI/UX

| Week | Feature | Tasks |
|------|---------|-------|
| 1-2 | Frontend Scaffold | Next.js setup, shadcn/ui, auth integration, layout |
| 3-4 | FEAT-004: Coding UI | Clinical notes input, SSE streaming display, code cards |
| 5-6 | FEAT-006: Code Browser | Hierarchical tree view, semantic search, code detail |
| 6 | FEAT-005: Export (Frontend) | Export UI dialog, format selection, download |
| 7 | Polish & Accessibility | WCAG audit, keyboard nav, responsive testing |

---

## Parallel Timeline (Gantt View)

```
Week:    1        2        3        4        5        6        7        8        9
         |--------|--------|--------|--------|--------|--------|--------|--------|

Track A: [Runway ][FEAT-001 Ingest  ][FEAT-002 RAG    ][FEAT-008    ][Benchmark ]
Track B: [FEAT-007 Auth    ][FEAT-003 API    ][FEAT-005 Exp][FEAT-009][Docs/Test ]
Track C:          [Scaffold ][FEAT-004 UI              ][FEAT-006   ][FEAT-005UI][Polish]

Gates:        G1       G2            G3           G4           G5            G6
```

### Gates

| Gate | Week | Criteria |
|------|------|----------|
| G1 | End of Week 1 | Runway complete: Docker running, DB schema applied, Qdrant collection created |
| G2 | End of Week 3 | Data ingested: 98K+ codes in DB, 130K+ chunks in Qdrant |
| G3 | End of Week 4 | RAG pipeline functional: 90%+ retrieval accuracy on benchmark |
| G4 | End of Week 5 | API live: SSE streaming works end-to-end, auth integrated |
| G5 | End of Week 7 | UI functional: Complete coding workflow in browser |
| G6 | End of Week 9 | Release ready: All features integrated, tested, documented |

---

## Synchronization Points

Points where tracks must sync before proceeding:

| Sync Point | Tracks | Trigger | Handoff |
|------------|--------|---------|---------|
| DB Schema Ready | A -> B, C | Runway complete | B and C can start building against schema |
| Data Available | A -> B, C | FEAT-001 complete | B can build code browser API, C can plan UI against real data |
| RAG Pipeline Ready | A -> B | FEAT-002 complete | B integrates pipeline into API endpoints |
| API Ready | B -> C | FEAT-003 complete | C connects frontend to real API (replaces mocks) |
| Auth Ready | B -> C | FEAT-007 complete | C integrates login flow |
| Export Backend Ready | B -> C | FEAT-005 backend complete | C builds export UI against real endpoints |

---

## Agent/Resource Allocation

For AI-agent-driven development, each track maps to an agent with specialized context:

| Track | Agent Profile | Context Window Priority |
|-------|--------------|------------------------|
| Track A | Data/AI agent | ICD-10-CM XML schemas, embedding docs, Qdrant API, RAG patterns |
| Track B | API agent | FastAPI docs, SSE spec, OIDC/JWT, HL7 FHIR R4, PostgreSQL RLS |
| Track C | Frontend agent | Next.js docs, shadcn/ui components, SSE client, React patterns |

### Agent Handoff Protocol

1. Track A completes FEAT-001 -> commits ingestion code -> Track B picks up data layer
2. Track A completes FEAT-002 -> exports pipeline interface -> Track B integrates into API
3. Track B completes FEAT-003 -> publishes OpenAPI spec -> Track C builds against spec
4. All tracks sync at gates for integration testing

---

## Risk Mitigation for Parallel Execution

| Risk | Mitigation |
|------|------------|
| Track C blocked waiting for Track B API | Track C uses mock API responses matching OpenAPI spec |
| Track B blocked waiting for Track A RAG pipeline | Track B builds API scaffolding with stub pipeline responses |
| Integration issues at sync points | Define interfaces/contracts early (Week 1), test against contracts |
| Single point of failure in Track A | Track A is on the critical path; prioritize and monitor closely |
