# Dependency Graph

## Initiative: INIT-001 Medical Coding Platform
## Last Updated: 2026-06-16

---

## Feature Dependencies

```
                    [Architecture Runway]
                           |
                           v
                    [FEAT-001: Data Ingestion]
                           |
              +------------+------------+
              |                         |
              v                         v
    [FEAT-002: RAG Pipeline]    [FEAT-006: Code Browser]*
              |
              v
    [FEAT-003: Coding API]
              |
    +---------+---------+-------------------+
    |         |         |                   |
    v         v         v                   v
[FEAT-004] [FEAT-005] [FEAT-009]    [FEAT-007: Auth]
Coding UI   Export    EMR API              |
    |         |                            v
    +----+----+                    [FEAT-008: Multi-Std]
         |
         v
    [R2 Release]

* FEAT-006 depends on FEAT-001 for data and FEAT-003 for API endpoints
```

---

## Dependency Matrix

| Feature | Depends On | Blocks |
|---------|-----------|--------|
| Architecture Runway | (none) | FEAT-001 |
| FEAT-001: Data Ingestion | Architecture Runway | FEAT-002, FEAT-006, FEAT-008 |
| FEAT-002: RAG Pipeline | FEAT-001 | FEAT-003 |
| FEAT-003: Coding API | FEAT-002 | FEAT-004, FEAT-005, FEAT-009 |
| FEAT-004: Coding UI | FEAT-003 | R2 Release |
| FEAT-005: Export | FEAT-003, FEAT-004 | R2 Release |
| FEAT-006: Code Browser | FEAT-001, FEAT-003 | R2 Release |
| FEAT-007: Multi-Tenant Auth | Architecture Runway | FEAT-009 |
| FEAT-008: Multi-Standard Support | FEAT-001, FEAT-002 | (none -- architectural enhancement) |
| FEAT-009: EMR Integration API | FEAT-003, FEAT-007 | (none -- standalone) |

---

## Critical Path

The critical path determines the minimum time to deliver the full platform:

```
Runway -> FEAT-001 -> FEAT-002 -> FEAT-003 -> FEAT-004 -> FEAT-005 -> R2 Release
 1 wk     1.5 wks     1.5 wks     1 wk       1.5 wks     1 wk
                                                            Total: ~7.5 weeks
```

Features NOT on the critical path (can be parallelized):
- FEAT-006 (Code Browser) -- can start after FEAT-001 completes
- FEAT-007 (Auth) -- can start in parallel with FEAT-001
- FEAT-008 (Multi-Standard) -- can start after FEAT-001 completes
- FEAT-009 (EMR API) -- can start after FEAT-003 and FEAT-007 complete

---

## Dependency Risks

| Risk | Description | Mitigation |
|------|-------------|------------|
| FEAT-001 quality | If ingestion produces incomplete data, FEAT-002 retrieval accuracy suffers | Thorough validation step in FEAT-001 before proceeding |
| FEAT-002 latency | If RAG pipeline is slow, FEAT-003 SSE streaming UX is degraded | Benchmark early, tune parameters, consider caching |
| FEAT-003 API stability | FEAT-004 and FEAT-005 depend on stable API contracts | Define API schemas early, use contract tests |
| FEAT-007 delayed | If auth is delayed, FEAT-009 EMR integration cannot proceed | FEAT-007 can start early (parallel with FEAT-001) |

---

## Integration Points

| Producer Feature | Consumer Feature | Integration Contract |
|-----------------|-----------------|---------------------|
| FEAT-001 | FEAT-002 | PostgreSQL `codes` table, Qdrant `icd10cm_chunks` collection |
| FEAT-002 | FEAT-003 | `RAGPipeline` Python class interface |
| FEAT-003 | FEAT-004 | REST API + SSE event schema |
| FEAT-003 | FEAT-005 | REST API (session and export endpoints) |
| FEAT-003 | FEAT-006 | REST API (code browser endpoints) |
| FEAT-003 | FEAT-009 | REST API (EMR coding endpoint) |
| FEAT-007 | FEAT-003 | Auth middleware (JWT validation, RBAC) |
| FEAT-007 | FEAT-009 | API key authentication |
| FEAT-008 | FEAT-001 | Parser interface, `coding_standards` table |
| FEAT-008 | FEAT-002 | Standard-aware collection routing |
