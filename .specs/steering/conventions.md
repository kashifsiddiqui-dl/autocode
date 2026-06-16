# Coding Conventions

Standards and practices for all code written in the Auto Code project. These conventions are enforced by tooling (linters, formatters, pre-commit hooks, CI checks) wherever possible.

---

## Python (Backend)

### Runtime & Version
- **Python 3.12+** (required for modern typing syntax, performance improvements)
- **Package manager:** `uv` (fast, reliable) with `pyproject.toml`
- **Virtual environment:** `.venv/` (created via `uv venv`)

### Code Style & Formatting
- **Formatter:** `ruff format` (Black-compatible, faster)
- **Linter:** `ruff check` with the following rule sets enabled:
  - `E` / `W` (pycodestyle errors and warnings)
  - `F` (pyflakes)
  - `I` (isort-compatible import sorting)
  - `UP` (pyupgrade - modern Python syntax)
  - `S` (bandit - security checks)
  - `B` (flake8-bugbear)
  - `A` (flake8-builtins)
  - `C4` (flake8-comprehensions)
  - `SIM` (flake8-simplify)
  - `RUF` (ruff-specific rules)
- **Line length:** 100 characters
- **Quote style:** Double quotes (`"`)
- **Trailing commas:** Always on multi-line constructs
- **Import order:** stdlib, third-party, local (enforced by ruff `I` rules)

### Type Checking
- **Type checker:** `mypy` in strict mode
- **All functions must have type annotations.** No untyped function signatures.
- **Use modern syntax:**
  - `str | None` not `Optional[str]`
  - `list[str]` not `List[str]`
  - `dict[str, int]` not `Dict[str, int]`
- **Pydantic models** for all data structures crossing boundaries (API request/response, config, domain objects)
- `# type: ignore` requires a comment explaining why

### Async
- **All I/O operations must be async.** Database queries, HTTP requests, file reads in the API path.
- **Use `async def` for all FastAPI endpoint functions.**
- **Use `asyncio.gather()`** for concurrent independent operations (e.g., parallel vector searches).
- **Never use synchronous blocking calls** (`time.sleep`, synchronous `requests`, synchronous DB drivers) in async code paths. Use `asyncio.sleep`, `httpx`, and `asyncpg`/`sqlalchemy[asyncio]`.
- **Exception:** CPU-bound work (embedding computation, XML parsing) should run in a thread pool via `asyncio.to_thread()` or be in separate non-async pipeline scripts.

### Pydantic
- **All API request/response models** use Pydantic `BaseModel` with `model_config = ConfigDict(strict=True)`.
- **Prefer `Field()` with descriptions** for all model fields that appear in API docs.
- **Use validators** (`@field_validator`, `@model_validator`) for business rule validation.
- **Naming:** Request models end in `Request`, response models end in `Response`. Example: `CodingQueryRequest`, `CodingResultResponse`.

### FastAPI Conventions
- **Router organization:** One router file per domain (`routers/coding.py`, `routers/auth.py`, `routers/admin.py`).
- **Dependency injection:** Use `Depends()` for authentication, database sessions, tenant context, and service instances.
- **Path operations:** Use descriptive operation IDs and tags.
- **Error responses:** Raise `HTTPException` with appropriate status codes. Use custom exception handlers for domain errors.
- **Middleware order:** CORS -> RequestID -> Logging -> Authentication -> TenantContext -> RateLimiting.

### Testing
- **Framework:** `pytest` with `pytest-asyncio` for async tests
- **Test file naming:** `test_<module>.py` in a `tests/` directory mirroring the source structure
- **Fixtures:** Use `conftest.py` for shared fixtures (database sessions, test clients, mock providers)
- **Coverage target:** 80% line coverage minimum, 90% for core pipeline code
- **Test categories:**
  - `tests/unit/` - Pure logic tests, no I/O, fast
  - `tests/integration/` - Tests with real database/Qdrant (Docker), marked with `@pytest.mark.integration`
  - `tests/e2e/` - Full API tests via `httpx.AsyncClient`

### Naming Conventions
- **Files/modules:** `snake_case.py` (e.g., `llm_provider.py`, `chunk_builder.py`)
- **Classes:** `PascalCase` (e.g., `ClaudeProvider`, `CodingResult`)
- **Functions/methods:** `snake_case` (e.g., `build_chunks`, `search_codes`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `MAX_CONTEXT_TOKENS`, `DEFAULT_TOP_K`)
- **Private members:** Single underscore prefix (`_internal_method`)
- **Protected/internal modules:** Single underscore prefix (`_utils.py`) -- rarely needed

### Error Handling
- **Use custom exception classes** for domain errors (e.g., `CodeNotFoundError`, `TenantNotFoundError`, `LLMProviderError`).
- **Never catch bare `Exception`** except at the top-level error handler.
- **Log exceptions with structured context** (request ID, tenant ID, user ID, operation).
- **Fail fast on configuration errors** (missing env vars, invalid settings) at startup, not at request time.

### Documentation
- **Docstrings:** Google-style docstrings on all public functions, classes, and modules.
- **No inline comments** that merely restate the code. Comments explain WHY, not WHAT.
- **ADRs** for architectural decisions (in `decisions/` directory).

---

## TypeScript (Frontend)

### Runtime & Version
- **Node.js 20 LTS+**
- **Package manager:** `pnpm`
- **Framework:** Next.js 15+ with App Router
- **TypeScript:** Strict mode (`"strict": true` in tsconfig.json)

### Code Style & Formatting
- **Formatter:** Prettier
  - Semi: true
  - Single quotes: true (for consistency with JSX attribute convention in the ecosystem)
  - Trailing commas: `all`
  - Print width: 100
  - Tab width: 2
- **Linter:** ESLint with:
  - `@typescript-eslint/recommended`
  - `eslint-config-next`
  - `eslint-plugin-react-hooks`
  - `eslint-plugin-jsx-a11y`

### React & Next.js
- **App Router** exclusively. No Pages Router.
- **Server Components by default.** Only use `'use client'` when the component needs interactivity (state, effects, event handlers, browser APIs).
- **Server Actions** for form submissions and mutations. Avoid client-side `fetch` for mutations.
- **Suspense boundaries** around async components with meaningful loading fallbacks.
- **Error boundaries** (`error.tsx`) at route segment level.
- **Metadata API** for page titles and descriptions.

### Component Architecture
- **File naming:** `kebab-case.tsx` for component files (e.g., `code-result-card.tsx`, `coding-input.tsx`).
- **Component naming:** `PascalCase` (e.g., `CodeResultCard`, `CodingInput`).
- **One component per file** for named exports. Utility/helper subcomponents may coexist if small.
- **Props interfaces:** Named `{ComponentName}Props` and defined above the component.
- **UI primitives:** shadcn/ui components (installed, not imported from a package). Customize via Tailwind.
- **Icons:** `lucide-react`.

### Styling
- **Tailwind CSS** exclusively. No CSS modules, styled-components, or inline style objects.
- **Design tokens** via Tailwind theme extension in `tailwind.config.ts` (colors, spacing, fonts).
- **Class merging:** Use `cn()` utility (clsx + tailwind-merge) for conditional classes.
- **Responsive design:** Mobile-first (`sm:`, `md:`, `lg:` breakpoints). Desktop is the primary target but layout must not break on tablet.
- **Dark mode:** Use Tailwind `dark:` variant. All components must support both modes.

### State Management
- **Server state:** React Server Components + Suspense. No client-side data fetching for initial page loads.
- **Client state:** `useState` and `useReducer` for local component state.
- **Shared client state:** Zustand (lightweight) for cross-component state that cannot use URL params.
- **URL state:** Use `useSearchParams` and `usePathname` for filterable/shareable state (search filters, pagination).
- **No Redux.** Over-engineered for this application's needs.

### Data Fetching
- **API client:** Generated from OpenAPI spec or hand-written with `fetch` + type-safe wrappers.
- **No `axios`.** Use native `fetch` (supported in Next.js with caching/revalidation controls).
- **Streaming:** Use `ReadableStream` + `TextDecoderStream` for SSE-based LLM streaming responses.
- **Error handling:** API errors surfaced via error boundaries or inline error states. Never swallow errors silently.

### Testing
- **Unit tests:** Vitest + React Testing Library
- **E2E tests:** Playwright
- **Test file naming:** `*.test.tsx` co-located with the component, or in `__tests__/` directory
- **Accessibility testing:** `eslint-plugin-jsx-a11y` rules enforced + manual screen reader testing for key flows

---

## SQL & Database

### ORM & Migrations
- **ORM:** SQLAlchemy 2.0+ with async engine (`asyncpg` driver)
- **Migrations:** Alembic with auto-generation from SQLAlchemy models
- **Migration naming:** `{revision_id}_{descriptive_slug}.py` (auto-generated by Alembic)
- **No raw SQL in application code** except for performance-critical queries documented with a comment explaining why the ORM is insufficient.

### Schema Conventions
- **Table naming:** Plural `snake_case` (e.g., `users`, `coding_sessions`, `tenant_settings`)
- **Column naming:** `snake_case` (e.g., `tenant_id`, `created_at`, `is_billable`)
- **Primary keys:** `id` column, UUID type (`uuid_generate_v4()` default), never auto-incrementing integers (prevents enumeration attacks)
- **Foreign keys:** Named `{referenced_table_singular}_id` (e.g., `user_id`, `tenant_id`)
- **Timestamps:** `created_at` (default `now()`) and `updated_at` (trigger-updated) on all tables
- **Soft deletes:** `deleted_at` timestamp (nullable) instead of hard deletes for audit-sensitive tables
- **Indexes:** Create indexes on all foreign key columns and frequently filtered columns. Name format: `ix_{table}_{column}`
- **Constraints:** Use CHECK constraints for enum-like fields. Use UNIQUE constraints where business logic requires it.

### Multi-Tenancy
- **Every tenant-scoped table** has a `tenant_id UUID NOT NULL` column with a foreign key to `tenants.id`.
- **Row-level security (RLS):** PostgreSQL RLS policies enforce tenant isolation at the database level, not just the application level.
- **All queries** through the ORM automatically include `tenant_id` filtering via a SQLAlchemy session event or a scoped query helper.
- **Cross-tenant queries** are explicitly prohibited in application code. Admin/platform queries that span tenants must use a separate database role with RLS disabled, and must be restricted to admin endpoints with audit logging.

### Migration Rules
- **Never modify a deployed migration.** Create a new migration to alter or fix.
- **Every migration must be reversible** (implement both `upgrade()` and `downgrade()`).
- **Data migrations** (backfills, transformations) are separate from schema migrations.
- **Test migrations** against a snapshot of production data before deploying.

---

## Git

### Branching Strategy
- **`main`** - Production-ready code. Protected. Merge via PR only.
- **`develop`** - Integration branch. PRs merged here first. Deployed to staging.
- **Feature branches:** `feature/{ticket-id}-{short-description}` (e.g., `feature/CA-01-coding-endpoint`)
- **Bug fix branches:** `fix/{ticket-id}-{short-description}` (e.g., `fix/HA-03-feedback-null-check`)
- **Hotfix branches:** `hotfix/{description}` (branch from `main`, merge to both `main` and `develop`)

### Commit Messages
- **Format:** [Conventional Commits](https://www.conventionalcommits.org/) specification.
- **Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`, `perf`, `build`
- **Scope (optional):** Module or area affected (e.g., `feat(ingestion):`, `fix(auth):`, `docs(adr):`)
- **Subject:** Imperative mood, lowercase, no period. Max 72 characters.
- **Body (optional):** Explain what and why, not how. Wrap at 100 characters.

**Examples:**
```
feat(rag): implement reciprocal rank fusion for multi-vector search
fix(auth): handle expired refresh token with concurrent requests
docs(adr): add ADR-005 for LLM abstraction layer
chore: update qdrant-client to 1.12.0
test(ingestion): add unit tests for tabular XML parser
```

### Pull Requests
- **Title:** Follows conventional commit format.
- **Description:** What changed, why, how to test, any breaking changes.
- **Size:** Keep PRs small and focused. Prefer multiple small PRs over one large PR.
- **Reviews:** At least one approval required before merge.
- **CI must pass:** All lint, type check, and test checks green before merge.
- **Squash merge** to `develop`/`main` for a clean linear history.

---

## Environment Variables

### Naming
- **Prefix by service:** `DATABASE_URL`, `QDRANT_URL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `AZURE_AD_*`
- **Boolean values:** Use `true`/`false` (lowercase string), parsed by Pydantic Settings.
- **All env vars documented** in `.env.example` with descriptions and example values.
- **Secrets never in code or committed files.** Use `.env.local` (gitignored) for local development, Key Vault for production.

### Configuration Loading
- **Pydantic Settings** (`pydantic-settings`) for type-safe configuration with environment variable binding.
- **Fail fast:** Missing required env vars cause startup failure with a clear error message listing the missing variables.
- **No defaults for secrets.** API keys, database credentials, and JWT signing keys must always be explicitly set.

---

## Logging

- **Library:** Python `structlog` for structured JSON logging.
- **Log levels:** `DEBUG` (development only), `INFO` (request lifecycle, business events), `WARNING` (recoverable issues), `ERROR` (failures requiring attention), `CRITICAL` (system-level failures).
- **Context:** Every log entry includes `request_id`, `tenant_id`, `user_id` (when available), `operation`, and `duration_ms`.
- **No PHI in logs.** Clinical descriptions and patient information must never appear in log output. Log only code identifiers, session IDs, and metadata.
- **Frontend logging:** Console in development. Structured JSON to a logging endpoint in production (for server-side aggregation).
