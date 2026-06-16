# Project Structure Rules

Defines where files go, how they are named, and what belongs in each directory. All contributors must follow these rules. Automated tooling enforces naming conventions where possible.

---

## Top-Level Directory Layout

```
autocode/
├── .github/                    # GitHub Actions workflows, PR templates, issue templates
│   └── workflows/
├── .specs/                     # Project specifications and steering documents
│   └── steering/               # Product, conventions, structure (this file)
├── backend/                    # Python FastAPI application
│   ├── src/
│   │   └── autocode/           # Main Python package
│   ├── tests/
│   ├── alembic/                # Database migrations
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/                   # Next.js TypeScript application
│   ├── src/
│   │   ├── app/                # Next.js App Router pages
│   │   ├── components/         # React components
│   │   ├── lib/                # Utilities, API client, hooks
│   │   └── types/              # TypeScript type definitions
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── data/                       # Source data files (gitignored, large)
│   └── ICD-10-CM/              # ICD-10-CM data files (XML, TXT, PDF)
├── decisions/                  # Architecture Decision Records (ADRs)
├── infra/                      # Infrastructure as Code
│   ├── terraform/              # Terraform modules for Azure
│   └── docker/                 # Docker Compose files
├── memory/                     # Persistent project knowledge
├── planning/                   # Roadmap, backlog, sprint tracking
├── scripts/                    # Utility scripts (setup, data processing, etc.)
├── .gitignore
├── CLAUDE.md                   # AI assistant context
└── docker-compose.yml          # Local development environment
```

---

## Backend Structure (`backend/`)

```
backend/
├── src/
│   └── autocode/
│       ├── __init__.py
│       ├── main.py                     # FastAPI app factory, lifespan, middleware
│       ├── config.py                   # Pydantic Settings configuration
│       ├── dependencies.py             # FastAPI Depends() factories
│       │
│       ├── api/                        # API layer (routers, schemas)
│       │   ├── __init__.py
│       │   ├── routers/
│       │   │   ├── __init__.py
│       │   │   ├── coding.py           # POST /api/v1/code, POST /api/v1/code/stream
│       │   │   ├── codes.py            # GET /api/v1/codes/{code}, GET /api/v1/codes/search
│       │   │   ├── auth.py             # GET /api/v1/auth/login, /callback, /refresh, /logout
│       │   │   ├── admin.py            # User management, tenant settings, audit logs
│       │   │   └── health.py           # GET /api/v1/health
│       │   ├── schemas/                # Pydantic request/response models
│       │   │   ├── __init__.py
│       │   │   ├── coding.py           # CodingQueryRequest, CodingResultResponse
│       │   │   ├── codes.py            # CodeDetailResponse, CodeSearchResponse
│       │   │   ├── auth.py             # LoginResponse, TokenResponse
│       │   │   └── admin.py            # UserResponse, TenantSettingsResponse
│       │   └── middleware/
│       │       ├── __init__.py
│       │       ├── auth.py             # JWT validation, get_current_user
│       │       ├── tenant.py           # Tenant context injection
│       │       ├── logging.py          # Request/response logging
│       │       └── rate_limit.py       # Rate limiting
│       │
│       ├── core/                       # Core business logic (framework-agnostic)
│       │   ├── __init__.py
│       │   ├── rag/                    # RAG pipeline
│       │   │   ├── __init__.py
│       │   │   ├── retriever.py        # Vector search, RRF fusion
│       │   │   ├── generator.py        # LLM prompt assembly, response parsing
│       │   │   ├── validator.py        # Output validation, hallucination detection
│       │   │   └── pipeline.py         # End-to-end RAG orchestration
│       │   ├── llm/                    # LLM abstraction layer
│       │   │   ├── __init__.py
│       │   │   ├── base.py             # LLMProvider ABC
│       │   │   ├── factory.py          # LLMFactory
│       │   │   ├── anthropic.py        # ClaudeProvider
│       │   │   ├── openai.py           # OpenAIProvider
│       │   │   └── orchestrator.py     # Fallback, retry logic
│       │   ├── embeddings/             # Embedding generation
│       │   │   ├── __init__.py
│       │   │   ├── openai.py           # text-embedding-3-large client
│       │   │   ├── pubmedbert.py       # PubMedBERT inference
│       │   │   └── sparse.py           # BM25 sparse vector computation
│       │   └── auth/                   # Authentication logic
│       │       ├── __init__.py
│       │       ├── oidc.py             # Azure AD OIDC flow
│       │       ├── jwt.py              # Auto Code JWT creation/validation
│       │       └── sessions.py         # Session management, refresh token rotation
│       │
│       ├── db/                         # Database layer
│       │   ├── __init__.py
│       │   ├── engine.py               # SQLAlchemy async engine setup
│       │   ├── session.py              # Async session factory
│       │   ├── models/                 # SQLAlchemy ORM models
│       │   │   ├── __init__.py
│       │   │   ├── tenant.py           # Tenant, TenantSettings
│       │   │   ├── user.py             # User, UserRole
│       │   │   ├── session.py          # Session (auth sessions)
│       │   │   ├── coding.py           # CodingSession, Feedback
│       │   │   └── audit.py            # AuthAuditLog
│       │   └── repositories/           # Data access layer
│       │       ├── __init__.py
│       │       ├── tenant.py
│       │       ├── user.py
│       │       ├── coding.py
│       │       └── audit.py
│       │
│       ├── vector/                     # Qdrant vector store integration
│       │   ├── __init__.py
│       │   ├── client.py              # Qdrant client wrapper
│       │   ├── collections.py         # Collection creation, schema management
│       │   └── search.py              # Search operations (dense, sparse, hybrid)
│       │
│       └── ingestion/                 # Data ingestion pipeline
│           ├── __init__.py
│           ├── parsers/               # XML/TXT file parsers
│           │   ├── __init__.py
│           │   ├── tabular.py         # Tabular list XML parser
│           │   ├── index.py           # Alphabetic index XML parser
│           │   ├── drug.py            # Drug table XML parser
│           │   ├── neoplasm.py        # Neoplasm table XML parser
│           │   └── eindex.py          # External cause index parser
│           ├── chunker.py             # Chunk builder (context inheritance)
│           ├── embedder.py            # Batch embedding orchestrator
│           ├── loader.py              # Qdrant batch upsert
│           └── pipeline.py            # End-to-end ingestion orchestrator
│
├── tests/
│   ├── conftest.py                    # Shared fixtures
│   ├── unit/
│   │   ├── core/
│   │   │   ├── test_retriever.py
│   │   │   ├── test_generator.py
│   │   │   ├── test_validator.py
│   │   │   └── test_llm_factory.py
│   │   ├── ingestion/
│   │   │   ├── test_tabular_parser.py
│   │   │   ├── test_index_parser.py
│   │   │   ├── test_chunker.py
│   │   │   └── test_embedder.py
│   │   └── db/
│   │       └── test_repositories.py
│   ├── integration/
│   │   ├── test_qdrant_search.py
│   │   ├── test_rag_pipeline.py
│   │   └── test_auth_flow.py
│   └── e2e/
│       ├── test_coding_api.py
│       └── test_admin_api.py
│
├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── versions/                      # Migration files
│
├── pyproject.toml
├── Dockerfile
└── .env.example
```

### Backend Rules

1. **`api/` is thin.** Routers contain only request validation, dependency injection, and response formatting. Business logic lives in `core/`.
2. **`core/` is framework-agnostic.** No FastAPI imports in `core/`. It should be testable without running the web framework.
3. **`db/models/` defines the schema.** SQLAlchemy models are the source of truth for the database schema. Alembic auto-generates migrations from these models.
4. **`db/repositories/` is the data access layer.** All database queries go through repository classes. No direct session usage in routers or core logic.
5. **`ingestion/` is a standalone pipeline.** It can be run independently (via CLI script) without starting the FastAPI server. It imports from `core/` and `vector/` but not from `api/`.
6. **No circular imports.** Dependency direction: `api/` -> `core/` -> `db/`, `vector/`. Never the reverse.

---

## Frontend Structure (`frontend/`)

```
frontend/
├── src/
│   ├── app/                           # Next.js App Router
│   │   ├── layout.tsx                 # Root layout (providers, global styles)
│   │   ├── page.tsx                   # Landing / redirect to /code
│   │   ├── login/
│   │   │   └── page.tsx               # Login page
│   │   ├── code/
│   │   │   ├── layout.tsx             # Coding assistant layout
│   │   │   └── page.tsx               # Main coding assistant page
│   │   ├── search/
│   │   │   └── page.tsx               # Code search page
│   │   ├── history/
│   │   │   ├── page.tsx               # Session history list
│   │   │   └── [id]/
│   │   │       └── page.tsx           # Session detail page
│   │   ├── settings/
│   │   │   ├── page.tsx               # User settings
│   │   │   └── admin/
│   │   │       ├── page.tsx           # Admin dashboard
│   │   │       ├── users/
│   │   │       │   └── page.tsx       # User management
│   │   │       └── audit/
│   │   │           └── page.tsx       # Audit log viewer
│   │   └── api/                       # Next.js API routes (BFF)
│   │       └── auth/
│   │           └── [...slug]/
│   │               └── route.ts       # Auth callback handling
│   │
│   ├── components/                    # React components
│   │   ├── ui/                        # shadcn/ui base components
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── badge.tsx
│   │   │   └── ...
│   │   ├── coding/                    # Coding assistant components
│   │   │   ├── coding-input.tsx       # Clinical description textarea
│   │   │   ├── code-result-card.tsx   # Individual code recommendation
│   │   │   ├── code-result-list.tsx   # List of recommendations
│   │   │   ├── confidence-badge.tsx   # Visual confidence indicator
│   │   │   ├── warning-badge.tsx      # Excludes1, Code First warnings
│   │   │   └── streaming-response.tsx # SSE streaming display
│   │   ├── code-detail/              # Code detail view components
│   │   │   ├── code-detail-panel.tsx
│   │   │   ├── hierarchy-breadcrumb.tsx
│   │   │   ├── excludes-list.tsx
│   │   │   └── seventh-char-selector.tsx
│   │   ├── search/                   # Search components
│   │   │   ├── search-input.tsx
│   │   │   ├── search-filters.tsx
│   │   │   └── search-results.tsx
│   │   ├── history/                  # History components
│   │   │   ├── session-list.tsx
│   │   │   ├── session-card.tsx
│   │   │   └── feedback-form.tsx
│   │   ├── layout/                   # Layout components
│   │   │   ├── sidebar.tsx
│   │   │   ├── header.tsx
│   │   │   ├── nav-link.tsx
│   │   │   └── user-menu.tsx
│   │   └── shared/                   # Shared/generic components
│   │       ├── loading-skeleton.tsx
│   │       ├── error-state.tsx
│   │       ├── empty-state.tsx
│   │       └── copy-button.tsx
│   │
│   ├── lib/                          # Utilities and shared logic
│   │   ├── api/                      # API client
│   │   │   ├── client.ts             # Base fetch wrapper with auth
│   │   │   ├── coding.ts             # Coding API functions
│   │   │   ├── codes.ts              # Code lookup API functions
│   │   │   ├── auth.ts               # Auth API functions
│   │   │   └── admin.ts              # Admin API functions
│   │   ├── hooks/                    # Custom React hooks
│   │   │   ├── use-streaming.ts      # SSE streaming hook
│   │   │   ├── use-auth.ts           # Authentication state hook
│   │   │   └── use-debounce.ts       # Input debouncing
│   │   ├── utils/                    # Pure utility functions
│   │   │   ├── cn.ts                 # Class name merging (clsx + twMerge)
│   │   │   ├── format.ts             # Date, number formatting
│   │   │   └── icd-code.ts           # ICD-10-CM code formatting/validation
│   │   └── stores/                   # Zustand stores (if needed)
│   │       └── session-store.ts      # Current coding session state
│   │
│   └── types/                        # TypeScript type definitions
│       ├── api.ts                     # API response types
│       ├── coding.ts                  # CodingResult, RetrievedChunk types
│       ├── auth.ts                    # User, Tenant, Role types
│       └── index.ts                   # Re-exports
│
├── public/
│   ├── favicon.ico
│   └── logo.svg
│
├── package.json
├── pnpm-lock.yaml
├── tsconfig.json
├── next.config.ts
├── tailwind.config.ts
├── postcss.config.js
├── .eslintrc.json
├── .prettierrc
├── Dockerfile
└── .env.example
```

### Frontend Rules

1. **`app/` contains only page-level components and layouts.** No reusable components in `app/`. Pages import from `components/`.
2. **`components/` is organized by feature domain**, not by component type. Group related components together (`coding/`, `search/`, `history/`).
3. **`components/ui/` is for shadcn/ui primitives only.** These are base-level UI components (button, input, card) that other components compose.
4. **`components/shared/` is for truly generic components** used across multiple features (loading states, error states, copy button).
5. **`lib/api/` is the sole API communication layer.** Components never call `fetch` directly. All API calls go through typed functions in `lib/api/`.
6. **`lib/hooks/` for custom hooks that encapsulate complex logic.** Simple `useState` does not need a custom hook.
7. **`types/` mirrors the backend's Pydantic schemas.** Keep frontend types in sync with backend response models.
8. **No `any` type.** Use `unknown` + type narrowing if the type is truly unknown. `any` is only acceptable in test files with a justifying comment.

---

## Documentation Structure

```
decisions/                         # Architecture Decision Records
├── 001-vector-db-qdrant.md
├── 002-chunking-strategy.md
├── 003-embedding-model.md
├── 004-auth-azure-ad.md
└── 005-llm-abstraction.md

memory/                            # Persistent project knowledge
├── glossary.md                    # Terminology definitions
└── product-vision.md              # Product vision and principles

planning/                          # Active planning documents
├── todo.md                        # Phase-by-phase task tracker
├── roadmap.md                     # Timeline and milestones
├── backlog.md                     # Feature backlog with priorities
└── current-sprint.md              # Current sprint focus and status

.specs/                            # Project specifications
└── steering/
    ├── product.md                 # Product context and positioning
    ├── conventions.md             # Coding conventions
    └── structure.md               # This file
```

### Documentation Rules

1. **ADRs are immutable once accepted.** To change a decision, create a new ADR that supersedes the old one. Update the old ADR's status to "Superseded by ADR-XXX."
2. **ADR numbering is sequential.** Never reuse a number. If ADR-003 is superseded, the replacement is ADR-006 (or whatever the next number is).
3. **Planning documents are living documents.** Update `todo.md`, `current-sprint.md`, and `backlog.md` as work progresses.
4. **Memory documents are reference material.** `glossary.md` and `product-vision.md` are updated when new terms or concepts are introduced, not on a schedule.
5. **No documentation duplication.** A concept should be defined in one place and referenced elsewhere. If the glossary defines "Excludes1," do not re-define it in an ADR -- reference the glossary.

---

## Naming Conventions Summary

| Item | Convention | Example |
|---|---|---|
| Python files | `snake_case.py` | `chunk_builder.py` |
| Python classes | `PascalCase` | `ClaudeProvider` |
| Python functions | `snake_case` | `build_chunks()` |
| Python constants | `UPPER_SNAKE_CASE` | `MAX_CONTEXT_TOKENS` |
| TypeScript files | `kebab-case.tsx` / `.ts` | `code-result-card.tsx` |
| React components | `PascalCase` | `CodeResultCard` |
| TypeScript types | `PascalCase` | `CodingResult` |
| CSS classes | Tailwind utilities | `className="flex items-center gap-2"` |
| Database tables | Plural `snake_case` | `coding_sessions` |
| Database columns | `snake_case` | `tenant_id` |
| API routes | `/api/v1/kebab-case` | `/api/v1/coding-sessions` |
| Environment variables | `UPPER_SNAKE_CASE` | `DATABASE_URL` |
| Git branches | `type/ticket-description` | `feature/CA-01-coding-endpoint` |
| ADR files | `NNN-slug.md` | `001-vector-db-qdrant.md` |
| Docker services | `kebab-case` | `autocode-api` |

---

## File Placement Decision Tree

When creating a new file, use this decision tree:

1. **Is it an API endpoint?** -> `backend/src/autocode/api/routers/`
2. **Is it a request/response schema?** -> `backend/src/autocode/api/schemas/`
3. **Is it business logic (not framework-specific)?** -> `backend/src/autocode/core/`
4. **Is it a database model?** -> `backend/src/autocode/db/models/`
5. **Is it a database query?** -> `backend/src/autocode/db/repositories/`
6. **Is it Qdrant-related?** -> `backend/src/autocode/vector/`
7. **Is it data parsing/ingestion?** -> `backend/src/autocode/ingestion/`
8. **Is it a React page?** -> `frontend/src/app/{route}/page.tsx`
9. **Is it a React component?** -> `frontend/src/components/{feature-domain}/`
10. **Is it an API client function?** -> `frontend/src/lib/api/`
11. **Is it a custom hook?** -> `frontend/src/lib/hooks/`
12. **Is it a TypeScript type?** -> `frontend/src/types/`
13. **Is it an architectural decision?** -> `decisions/`
14. **Is it a Terraform module?** -> `infra/terraform/`
15. **Is it a utility script?** -> `scripts/`
16. **Is it a CI/CD workflow?** -> `.github/workflows/`
17. **Does it not fit anywhere above?** -> Ask before creating. It probably needs a new directory or belongs in an existing one that was overlooked.
