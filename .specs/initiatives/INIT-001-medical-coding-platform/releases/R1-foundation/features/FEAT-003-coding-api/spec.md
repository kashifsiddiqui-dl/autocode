# FEAT-003: Coding API

## Status: Not Started
## Priority: P0
## Release: R1 Foundation
## Owner: TBD
## Estimated Effort: 1 week
## Depends On: FEAT-002

---

## Summary

Expose the RAG-based medical coding engine as a REST API with SSE (Server-Sent Events) streaming for real-time result delivery. The API includes the primary coding analysis endpoint, session management, and a code browser endpoint for hierarchical code lookup.

## Problem Statement

The RAG pipeline (FEAT-002) operates as an internal service. Clients (web UI, EMR integrations, CLI tools) need a well-defined HTTP API to submit clinical text, receive streaming coding suggestions, and manage coding sessions. SSE streaming is essential because the full pipeline takes several seconds, and users need progressive feedback.

## Functional Requirements

### FR-1: Coding Analysis Endpoint

```
POST /api/v1/coding/analyze
Content-Type: application/json
Accept: text/event-stream

Request Body:
{
  "clinical_text": "string (required, max 10000 chars)",
  "session_id": "uuid (optional -- creates new if omitted)",
  "patient": {
    "name": "string (optional)",
    "dob": "date (optional)",
    "mrn": "string (optional)",
    "gender": "string (optional)"
  },
  "options": {
    "max_results": "integer (default 10, max 25)",
    "min_confidence": "float (default 0.3)",
    "billable_only": "boolean (default false)",
    "chapter_filter": "string[] (optional)",
    "standard": "string (default 'icd10cm')",
    "version": "string (default 'latest')"
  }
}
```

SSE Response Events:

```
event: session
data: {"session_id": "uuid", "status": "processing"}

event: stage
data: {"stage": "retrieval", "status": "started"}

event: stage
data: {"stage": "retrieval", "status": "completed", "duration_ms": 450, "candidates": 30}

event: stage
data: {"stage": "reranking", "status": "started"}

event: stage
data: {"stage": "reranking", "status": "completed", "duration_ms": 200, "candidates": 15}

event: stage
data: {"stage": "analysis", "status": "started"}

event: code
data: {"code": "E11.9", "description": "Type 2 diabetes mellitus without complications", "confidence": 0.95, "reasoning": "...", "is_billable": true, "hierarchy": {...}, "excludes": {...}}

event: code
data: {"code": "I10", "description": "Essential (primary) hypertension", "confidence": 0.92, ...}

event: stage
data: {"stage": "validation", "status": "completed", "codes_validated": 5, "codes_removed": 0}

event: complete
data: {"session_id": "uuid", "total_codes": 5, "duration_ms": 3200}
```

### FR-2: Session Management Endpoints

```
# Get session details
GET /api/v1/coding/sessions/{session_id}
Response: Session object with patient info, clinical text, and coding results

# List sessions (paginated)
GET /api/v1/coding/sessions?page=1&per_page=20&status=draft
Response: Paginated list of sessions for the authenticated user

# Update coding result status (accept/reject)
PATCH /api/v1/coding/sessions/{session_id}/results/{result_id}
Body: {"status": "accepted" | "rejected"}

# Update session status
PATCH /api/v1/coding/sessions/{session_id}
Body: {"status": "completed" | "draft"}

# Delete session
DELETE /api/v1/coding/sessions/{session_id}
```

### FR-3: Code Browser Endpoints

```
# Get code hierarchy (chapters)
GET /api/v1/codes/chapters
Response: List of 22 ICD-10-CM chapters with code ranges

# Get sections within a chapter
GET /api/v1/codes/chapters/{chapter}/sections
Response: List of sections with code ranges

# Get codes within a section or category
GET /api/v1/codes/browse?parent={category_code}
Response: List of child codes under the given parent

# Get code details
GET /api/v1/codes/{code}
Response: Full code record with hierarchy, descriptions, includes, excludes, annotations

# Search codes
GET /api/v1/codes/search?q={query}&limit=20
Response: Semantic search results using the RAG retrieval (dense only, no LLM)
```

### FR-4: Health & Metadata Endpoints

```
# Health check
GET /api/v1/health
Response: {"status": "healthy", "services": {"postgres": "up", "qdrant": "up", "redis": "up"}}

# Supported standards
GET /api/v1/standards
Response: List of active coding standards with versions

# API metadata
GET /api/v1/info
Response: {"version": "1.0.0", "supported_standards": [...], "features": [...]}
```

### FR-5: Error Handling

Standard error response format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Clinical text exceeds maximum length of 10000 characters",
    "details": [
      {"field": "clinical_text", "issue": "max_length_exceeded", "max": 10000, "actual": 12500}
    ]
  }
}
```

Error codes:
- `VALIDATION_ERROR` (400) -- Invalid request parameters
- `AUTHENTICATION_ERROR` (401) -- Missing or invalid auth token
- `AUTHORIZATION_ERROR` (403) -- Insufficient permissions
- `NOT_FOUND` (404) -- Resource not found
- `RATE_LIMITED` (429) -- Too many requests
- `INTERNAL_ERROR` (500) -- Unexpected server error
- `SERVICE_UNAVAILABLE` (503) -- Downstream service unavailable (Qdrant, LLM API)

### FR-6: Rate Limiting

- 10 coding analysis requests per minute per user (configurable)
- 100 code browser requests per minute per user
- Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- Redis-backed sliding window counter

## Non-Functional Requirements

- **Response time**: SSE first event within 500ms, full response < 5s (p95)
- **Concurrency**: Handle 50 concurrent SSE connections
- **Availability**: Graceful degradation when downstream services are unavailable
- **Documentation**: OpenAPI 3.1 spec auto-generated from FastAPI
- **CORS**: Configurable allowed origins for frontend integration
- **Compression**: gzip response compression for non-SSE endpoints

## Technical Design

### FastAPI Application Structure

```
src/backend/app/
├── api/
│   ├── v1/
│   │   ├── endpoints/
│   │   │   ├── coding.py       # /coding/analyze, /coding/sessions
│   │   │   ├── codes.py        # /codes/chapters, /codes/browse, /codes/search
│   │   │   ├── health.py       # /health, /info, /standards
│   │   │   └── export.py       # /export (future - FEAT-005)
│   │   ├── schemas/
│   │   │   ├── coding.py       # Request/response Pydantic models
│   │   │   ├── codes.py
│   │   │   └── common.py       # Shared schemas (pagination, errors)
│   │   └── router.py           # APIRouter aggregation
│   └── deps.py                 # Dependency injection (DB session, auth, rate limiter)
├── core/
│   ├── config.py               # Pydantic Settings
│   └── security.py             # JWT validation, RBAC
├── services/
│   ├── coding/
│   │   └── analyzer.py         # Orchestrates RAG pipeline
│   └── rag/
│       └── pipeline.py         # RAG pipeline from FEAT-002
└── main.py                     # FastAPI app factory
```

### SSE Implementation

```python
async def analyze_streaming(request: CodingRequest) -> EventSourceResponse:
    async def event_generator():
        yield ServerSentEvent(event="session", data=json.dumps({...}))

        # Retrieval stage
        yield ServerSentEvent(event="stage", data=json.dumps({"stage": "retrieval", "status": "started"}))
        candidates = await rag_pipeline.retrieve(request.clinical_text)
        yield ServerSentEvent(event="stage", data=json.dumps({"stage": "retrieval", "status": "completed", ...}))

        # Reranking stage
        yield ServerSentEvent(event="stage", data=json.dumps({"stage": "reranking", "status": "started"}))
        reranked = await rag_pipeline.rerank(candidates)
        yield ServerSentEvent(event="stage", data=json.dumps({"stage": "reranking", "status": "completed", ...}))

        # LLM analysis stage (stream individual codes)
        yield ServerSentEvent(event="stage", data=json.dumps({"stage": "analysis", "status": "started"}))
        async for code_result in rag_pipeline.analyze_streaming(reranked):
            yield ServerSentEvent(event="code", data=json.dumps(code_result.dict()))

        # Completion
        yield ServerSentEvent(event="complete", data=json.dumps({...}))

    return EventSourceResponse(event_generator())
```

## Acceptance Criteria

- [ ] `POST /api/v1/coding/analyze` accepts clinical text and returns SSE stream
- [ ] SSE events follow the specified format (session, stage, code, complete)
- [ ] Codes stream progressively as they are identified
- [ ] Session is created and persisted in PostgreSQL
- [ ] `GET /api/v1/coding/sessions/{id}` returns session with results
- [ ] `PATCH /api/v1/coding/sessions/{id}/results/{id}` updates accept/reject status
- [ ] Code browser endpoints return correct hierarchy data
- [ ] Code search returns semantically relevant results
- [ ] Health endpoint reports status of all downstream services
- [ ] Rate limiting enforced and rate limit headers present
- [ ] Error responses follow standard format
- [ ] OpenAPI documentation generated and accessible at `/docs`
- [ ] CORS headers configured for frontend origin

## Test Plan

### Unit Tests
- Test Pydantic request/response model validation
- Test SSE event formatting
- Test rate limiting logic
- Test error response construction

### Integration Tests
- Test full coding analysis flow (submit text, receive SSE stream, verify codes)
- Test session CRUD operations
- Test code browser hierarchy navigation
- Test code search endpoint
- Test authentication and authorization
- Test rate limiting enforcement

### Load Tests
- 50 concurrent SSE connections with typical clinical notes
- Verify p95 latency < 5s under load
- Verify no memory leaks from open SSE connections
