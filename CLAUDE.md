# Auto Code

HIPAA-compliant RAG-based medical coding SaaS that takes patient clinical notes and produces ICD-10-CM codes using a vector database (Qdrant) combined with LLM reasoning (Anthropic Claude / OpenAI, configurable per tenant).

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 (App Router), React 19, TypeScript 5.x, Tailwind CSS, shadcn/ui, Zustand, TanStack Query |
| Backend | FastAPI, Python 3.12+, SQLAlchemy 2.0 (async), Alembic, Pydantic v2 |
| Database | PostgreSQL 17 (AWS RDS, encrypted, Multi-AZ) |
| Vector DB | Qdrant (self-hosted, named vectors, hybrid search with sparse + dense) |
| AI/ML | OpenAI text-embedding-3-large (1024d), PubMedBERT (clinical context), BAAI/bge-reranker-v2-m3, Anthropic Claude / OpenAI GPT (configurable) |
| Auth | Azure AD / Entra ID (OIDC), authlib, python-jose (JWT) |
| Infra | AWS (EC2, RDS, ALB, S3, KMS, WAF, CloudWatch, Route53, Secrets Manager), Terraform, Docker |
| CI/CD | GitHub Actions |
| Testing | pytest, pytest-asyncio, testcontainers, Vitest, Playwright |
| Monitoring | CloudWatch + Prometheus + Grafana |

---

## Project Structure

```
autocode/
├── CLAUDE.md                   # This file - Claude Code context
├── .specs/                     # Immutable project principles and steering docs
│   ├── constitution.md         # Core principles (patient safety, HIPAA, data sovereignty)
│   └── steering/
│       └── tech-stack.md       # Technology decisions with justifications
├── .ai/                        # AI agent configuration and context
├── docs/                       # External/user-facing documentation
├── memory/                     # Agent memory - session summaries, context
├── planning/                   # Active planning docs, roadmaps, epics
├── decisions/                  # Architecture Decision Records (ADRs)
├── data/
│   └── ICD-10-CM/              # ICD-10-CM April 2026 source data
│       ├── icd10cm-April-1-2026-XML/       # Tabular, index, drug, neoplasm, eindex XML
│       ├── icd10cm-table-and-index-April-1-2026/  # TXT codes, order files, XSD schemas, PDFs
│       ├── icd10cm-addenda-April-1-2026/    # Addenda PDFs (changes from prior version)
│       ├── icd10cm-Code Descriptions-April-1-2026/ # Order and codes file PDFs
│       └── ICD-10-CM April 1 2026 Guidelines Final.pdf  # Official coding guidelines
├── frontend/                   # Next.js 15 application
│   ├── app/                    # App Router pages and layouts
│   ├── components/             # React components (shadcn/ui based)
│   ├── lib/                    # Utilities, API client, hooks
│   ├── public/                 # Static assets
│   ├── package.json
│   └── tsconfig.json
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/                # Route handlers (versioned: /v1/)
│   │   ├── core/               # Config, security, dependencies
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic v2 request/response schemas
│   │   ├── services/           # Business logic layer
│   │   ├── rag/                # RAG pipeline (retrieval, reranking, prompting)
│   │   ├── ingestion/          # ICD-10-CM data parsing and vector ingestion
│   │   └── main.py             # FastAPI app entry point
│   ├── alembic/                # Database migrations
│   ├── tests/                  # pytest test suite
│   ├── pyproject.toml
│   └── alembic.ini
├── infra/
│   └── terraform/              # AWS infrastructure as code
├── docker-compose.yml          # Local development stack
├── Makefile                    # Developer commands
└── .gitignore
```

---

## Key Commands

| Command | Description |
|---------|-------------|
| `make dev` | Start local development environment (backend + frontend + databases) |
| `make ingest` | Parse and ingest ICD-10-CM data into Qdrant vector database |
| `make test` | Run all tests (backend pytest + frontend Vitest) |
| `make lint` | Lint everything (ruff + mypy + ESLint + Prettier) |
| `docker-compose up` | Start full stack via Docker (PostgreSQL, Qdrant, backend, frontend) |
| `make migrate` | Run Alembic database migrations |
| `make migrate-create` | Create a new Alembic migration |
| `make format` | Auto-format all code (ruff format + Prettier) |

---

## Coding Conventions

### Python (Backend)

- **Linting/Formatting**: ruff (linter + formatter), mypy (strict mode)
- **Style**: async/await everywhere (async SQLAlchemy, async HTTP clients)
- **Models**: Pydantic v2 for all schemas (use `model_validator`, `field_validator`, not v1 syntax)
- **ORM**: SQLAlchemy 2.0 style (mapped_column, DeclarativeBase, async sessions)
- **Migrations**: Alembic with auto-generation; every schema change requires a migration
- **Error handling**: Custom exception classes, never bare `except:`
- **Logging**: structlog with JSON output; never print()
- **Tests**: pytest + pytest-asyncio; use fixtures; testcontainers for integration tests
- **Docstrings**: Google style
- **Type hints**: Required on all function signatures

### TypeScript (Frontend)

- **Linting/Formatting**: ESLint (strict config) + Prettier
- **Components**: shadcn/ui component library, composed with Tailwind CSS
- **State**: Zustand for client state, TanStack Query for server state
- **Routing**: Next.js App Router (server components by default, `"use client"` only when needed)
- **Forms**: React Hook Form + Zod validation
- **API calls**: Generated TypeScript client from OpenAPI spec
- **Tests**: Vitest for unit tests, Playwright for E2E

### SQL / Database

- **Migrations**: Alembic only; never modify database schema manually
- **Multi-tenancy**: PostgreSQL Row-Level Security (RLS) policies on every tenant-scoped table
- **Naming**: snake_case for tables and columns; foreign keys as `<table>_id`
- **Indexes**: Always create indexes for foreign keys and frequently queried columns

---

## Architecture Notes

### Multi-Tenancy

All tenant isolation is enforced at the database level via PostgreSQL Row-Level Security (RLS). Every tenant-scoped table has a `tenant_id` column with an RLS policy. The backend sets `app.current_tenant` on each database session from the authenticated JWT. This means a query can never accidentally return data belonging to another tenant.

### Authentication

Azure AD / Entra ID via OIDC. The backend validates JWT tokens issued by Azure AD, extracts tenant and user claims, and sets the database session context for RLS. SSO is mandatory - there are no local username/password accounts.

### RAG Pipeline (4-Stage Retrieval)

The core medical coding pipeline follows four stages:

1. **Hybrid Search**: Parallel dense vector search (text-embedding-3-large) + sparse keyword search (BM25) against Qdrant. Named vectors allow querying both representations simultaneously.
2. **Metadata Filtering**: Filter results by ICD-10-CM chapter, category, code type, and validity period. Ensures only currently valid codes are returned.
3. **Reranking**: BAAI/bge-reranker-v2-m3 cross-encoder reranks the merged candidate set for clinical relevance to the input note.
4. **Hierarchy Expansion**: For each top candidate code, expand the ICD-10-CM hierarchy (parent categories, includes/excludes notes, code-first/use-additional instructions) to give the LLM full context for final code assignment.

### Negative Prompting

The LLM is explicitly instructed to ONLY use the retrieved ICD-10-CM context for code assignment. It must NEVER rely on its training data for medical codes. If the retrieved context is insufficient, it must say so rather than guess. Every assigned code must include a citation to the specific ICD-10-CM entry that supports it.

### Data Pipeline

ICD-10-CM April 2026 data (XML tabular, index, drug index, neoplasm table, eindex, plus addenda) is parsed, chunked with hierarchy-aware boundaries, embedded with both dense and sparse vectors, and stored in Qdrant with rich metadata (chapter, block, category, code, validity dates, includes/excludes, instructional notes).

---

## HIPAA Compliance Requirements

- **Encryption at rest**: AWS RDS encryption (AES-256 via KMS), Qdrant volume encryption
- **Encryption in transit**: TLS 1.2+ everywhere (ALB termination, internal service communication)
- **Audit logging**: Every API request logged with user, tenant, action, timestamp; stored immutably
- **PHI handling**: Clinical notes are processed in-memory, never persisted in logs or vector DB; only coding results are stored
- **Access controls**: RBAC with principle of least privilege; Azure AD groups mapped to application roles
- **BAA**: Required with AWS, Anthropic, and OpenAI before production deployment
- **Session management**: Short-lived JWTs (15 min access, 8 hour refresh), automatic expiry
- **Input validation**: All inputs validated via Pydantic; SQL injection prevented by ORM; XSS prevented by React
- **Rate limiting**: Per-tenant and per-user rate limits to prevent abuse
- **Data retention**: Configurable per-tenant retention policies with automated purging

---

## ICD-10-CM Data (April 2026)

Located in `data/ICD-10-CM/`. Source files are gitignored due to size but tracked via Git LFS or downloaded during setup.

| Directory | Contents |
|-----------|----------|
| `icd10cm-April-1-2026-XML/` | Tabular list, alphabetic index, drug index, neoplasm table, external cause index (XML) |
| `icd10cm-table-and-index-April-1-2026/` | Code files (TXT), order files (TXT), XSD schemas, PDF references |
| `icd10cm-addenda-April-1-2026/` | Addenda PDFs documenting changes from the prior release |
| `icd10cm-Code Descriptions-April-1-2026/` | Code description and order file documentation (PDF) |
| Root | ICD-10-CM April 1 2026 Guidelines Final.pdf - Official coding guidelines |

---

## Documentation Structure

| Directory | Purpose | When to Update |
|-----------|---------|---------------|
| `.specs/` | Immutable principles, architecture constitution, steering docs | Rarely - foundational decisions only |
| `.specs/steering/` | Technology choices, patterns, and conventions with justifications | When adding/changing tech |
| `memory/` | Agent session summaries, accumulated context | After each significant work session |
| `planning/` | Active epics, roadmaps, sprint plans | During planning and progress updates |
| `decisions/` | Architecture Decision Records (ADRs) | When making significant technical decisions |
| `docs/` | User-facing documentation, API docs, deployment guides | When features ship |
| `.ai/` | AI agent configuration, prompts, templates | When changing agent behavior |

**Workflow: Specs first, then code.** Before implementing any feature, the relevant spec or ADR must exist. Agents must maintain this documentation structure and update it as part of their work.

---

## Environment Variables

Key environment variables (see `.env.example` for full list):

- `DATABASE_URL` - PostgreSQL connection string
- `QDRANT_URL` - Qdrant server URL
- `QDRANT_API_KEY` - Qdrant authentication key
- `ANTHROPIC_API_KEY` - Anthropic API key (for Claude)
- `OPENAI_API_KEY` - OpenAI API key (for embeddings and optional GPT)
- `AZURE_AD_TENANT_ID` - Azure AD tenant for OIDC
- `AZURE_AD_CLIENT_ID` - Azure AD application client ID
- `AZURE_AD_CLIENT_SECRET` - Azure AD application client secret
- `AWS_KMS_KEY_ID` - KMS key for encryption
- `ENVIRONMENT` - `development`, `staging`, or `production`
