# Backend API Development Agent

## Role

Backend API development agent responsible for building and maintaining the Auto Code server application -- a FastAPI-based REST API powering the medical coding SaaS platform.

## Scope

All files within the following backend directories:

- `backend/app/api/` -- Route handlers and endpoint definitions
- `backend/app/models/` -- SQLAlchemy ORM models
- `backend/app/schemas/` -- Pydantic v2 request/response schemas
- `backend/app/services/` -- Business logic layer
- `backend/app/core/` -- Configuration, security, middleware, shared utilities

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (latest) |
| ORM | SQLAlchemy 2.0 (async, with asyncpg driver) |
| Validation | Pydantic v2 |
| Migrations | Alembic (async-compatible) |
| Database | PostgreSQL 16 |
| Auth | Azure AD OIDC (JWT validation) |
| Task Queue | (Future) Celery with Redis |
| Testing | pytest, pytest-asyncio, testcontainers |
| Language | Python 3.12+ |

## Responsibilities

### REST Endpoints

- **Coding API** (`/api/v1/code/`):
  - `POST /code/search` -- Submit clinical text for ICD-10-CM code lookup. Triggers the RAG pipeline.
  - `GET /code/stream` -- SSE endpoint for streaming coding results back to the client.
  - `GET /code/{code_id}` -- Retrieve detailed information for a specific ICD-10-CM code.
  - `GET /code/hierarchy/{chapter}` -- Browse the code hierarchy by chapter/section.

- **Sessions API** (`/api/v1/sessions/`):
  - `POST /sessions/` -- Create a new coding session.
  - `GET /sessions/` -- List sessions with pagination, filtering, and search.
  - `GET /sessions/{session_id}` -- Retrieve a session with its coding results.
  - `PATCH /sessions/{session_id}` -- Update session metadata (status, notes).
  - `DELETE /sessions/{session_id}` -- Soft-delete a session.

- **Export API** (`/api/v1/export/`):
  - `POST /export/csv` -- Export coding results as CSV.
  - `POST /export/pdf` -- Export coding results as formatted PDF.
  - `POST /export/fhir` -- (Future) Export as HL7 FHIR bundle.

- **Admin API** (`/api/v1/admin/`):
  - `GET /admin/tenants` -- List tenants (super-admin only).
  - `GET /admin/users` -- List users within a tenant.
  - `GET /admin/usage` -- Usage analytics and metrics.
  - `POST /admin/config` -- Update tenant-level configuration.

- **Health API** (`/api/v1/health/`):
  - `GET /health/` -- Basic liveness check.
  - `GET /health/ready` -- Readiness check (DB, Qdrant, external services).

### Database Models

- **User** -- Azure AD identity, tenant membership, roles, preferences.
- **Tenant** -- Organization entity, configuration, subscription tier.
- **CodingSession** -- A coding interaction: input text, timestamp, user, status.
- **CodingResult** -- Individual code result within a session: ICD-10-CM code, confidence, rank, user selection state.
- **AuditLog** -- Immutable audit trail: action, actor, target, timestamp, metadata.
- **ICD10Code** -- Denormalized ICD-10-CM code reference: code, descriptions, hierarchy, includes/excludes, notes.

### Business Logic

- **Coding Service**: Orchestrates the full coding flow -- receives clinical text, invokes RAG pipeline, streams results, persists session.
- **Session Service**: CRUD operations on coding sessions with proper tenant scoping.
- **Export Service**: Generates export files in requested formats with proper formatting and HIPAA-compliant headers.
- **User Service**: User provisioning (JIT from Azure AD), role management, preference storage.
- **Audit Service**: Records all auditable actions with structured metadata. Write-only from application perspective.

### Auth Middleware (Azure AD OIDC)

- JWT validation against Azure AD's JWKS endpoint with key caching.
- Token claims extraction: `sub`, `oid`, `tid` (tenant), `roles`, `email`.
- Just-In-Time user provisioning on first login.
- Role-based access control (RBAC): `user`, `admin`, `super_admin`.
- Request-scoped dependency that provides the authenticated user context.

### Multi-Tenancy (Row-Level Security)

- All data tables include a `tenant_id` column.
- PostgreSQL RLS policies enforce tenant isolation at the database level.
- Application-level middleware sets `app.current_tenant` on each database session.
- RLS is the last line of defense -- application code also filters by tenant, but RLS catches any bugs.
- Tenant context is derived from the authenticated user's Azure AD tenant ID.

### Audit Logging

- Every state-changing operation is logged to the `audit_log` table.
- Log entries include: action type, actor (user_id), target entity (type + id), before/after state diff, timestamp, IP address, request ID.
- Audit logs are append-only. No UPDATE or DELETE operations are permitted on the audit table.
- Designed for HIPAA compliance: tracks all access to and modifications of PHI.

## Key Files & Directories

```
backend/
  app/
    api/
      v1/
        endpoints/
          code.py           # Coding endpoints
          sessions.py       # Session CRUD
          export.py         # Export endpoints
          admin.py          # Admin endpoints
          health.py         # Health checks
        router.py           # V1 API router aggregation
      deps.py               # Shared dependencies (auth, db session, tenant)
    models/
      user.py               # User model
      tenant.py             # Tenant model
      session.py            # CodingSession model
      result.py             # CodingResult model
      audit.py              # AuditLog model
      icd10.py              # ICD10Code reference model
      base.py               # Base model with tenant_id, timestamps
    schemas/
      code.py               # Coding request/response schemas
      session.py            # Session schemas
      export.py             # Export schemas
      user.py               # User schemas
      common.py             # Shared schemas (pagination, errors)
    services/
      coding_service.py     # Coding orchestration
      session_service.py    # Session CRUD logic
      export_service.py     # Export generation
      user_service.py       # User management
      audit_service.py      # Audit logging
    core/
      config.py             # Pydantic Settings (env vars)
      security.py           # JWT validation, OIDC
      database.py           # Async SQLAlchemy engine + session
      middleware.py         # Tenant, logging, CORS middleware
      exceptions.py         # Custom exception classes
      logging.py            # Structured logging setup
    main.py                 # FastAPI app factory
  alembic/
    versions/               # Migration files
    env.py                  # Alembic environment config
  alembic.ini               # Alembic configuration
  pyproject.toml            # Python project config, dependencies
  requirements.txt          # Pinned dependencies
```

## Dependencies

- **RAG Pipeline**: The coding service calls into `backend/app/rag/` for retrieval and LLM processing. This is a direct Python import, not an HTTP call.
- **PostgreSQL**: Primary datastore for all relational data. Accessed via async SQLAlchemy.
- **Qdrant**: Vector database for code embeddings. Accessed via the RAG pipeline module, not directly from API code.
- **Azure AD**: External identity provider. JWKS endpoint for token validation.
- **Frontend**: Serves the Next.js frontend via nginx reverse proxy in production. API and frontend share the same domain.

## Guidelines

### Architecture Patterns

1. **Dependency Injection**: Use FastAPI's `Depends()` for all cross-cutting concerns: authentication, database sessions, tenant context, pagination parameters. Never import these directly in endpoint functions.
2. **Async/Await Throughout**: All database operations, HTTP calls, and I/O use `async`/`await`. No blocking calls in the async event loop. Use `asyncio.to_thread()` if calling synchronous libraries.
3. **Service Layer**: Endpoints are thin -- they validate input (via Pydantic), call the appropriate service, and return the response. Business logic lives in services, never in endpoint functions.
4. **Repository Pattern (Light)**: Services interact with models through SQLAlchemy queries. For complex queries, create dedicated query methods on the service or a repository helper. Avoid raw SQL except for RLS setup.
5. **Pydantic for Everything**: Request bodies, response models, configuration, and internal DTOs all use Pydantic v2 models. Use `model_config` for JSON schema customization.

### Database Conventions

- Table names are `snake_case` plural (e.g., `coding_sessions`, `audit_logs`).
- All tables have `id` (UUID), `created_at`, `updated_at` columns from the base model.
- All tenant-scoped tables have `tenant_id` (UUID, NOT NULL, indexed).
- Soft deletes use `deleted_at` timestamp (NULL means active).
- Alembic migrations are auto-generated but always reviewed and edited before committing.
- Use database-level constraints (UNIQUE, CHECK, FK) as the source of truth for data integrity.

### Error Handling

- Use custom exception classes that map to HTTP status codes.
- All exceptions include a machine-readable `error_code` and a human-readable `detail`.
- Never expose stack traces or internal details in API responses.
- Log full exception details server-side with request context.

### Security

- All endpoints require authentication except `/health/` and `/api/v1/auth/callback`.
- Admin endpoints require the `admin` or `super_admin` role.
- Input validation is strict -- reject unexpected fields, enforce max lengths, validate formats.
- SQL injection is prevented by SQLAlchemy's parameterized queries. Never use string formatting for SQL.
- Rate limiting is applied at the nginx/ALB level and optionally per-endpoint via middleware.
- No PHI in log messages. Use structured logging with PHI fields explicitly excluded.

### Performance

- Use database connection pooling via SQLAlchemy's async pool (pool_size, max_overflow configured per environment).
- Implement response caching for static data (ICD-10-CM code lookups) using Cache-Control headers.
- Paginate all list endpoints. Default page size is 20, max is 100.
- Use database indexes for all frequently queried columns (tenant_id, user_id, created_at, status).
