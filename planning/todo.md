# Auto Code - Task Tracker

## Phase 1: Foundation & Documentation [IN PROGRESS]

### Completed
- [x] Initialize Git repository
- [x] Create .gitignore with comprehensive exclusions
- [x] Acquire ICD-10-CM April 2026 data files (XML, TXT, PDF)
- [x] ADR-001: Vector database selection (Qdrant)
- [x] ADR-002: Chunking strategy (code-centric)
- [x] ADR-003: Embedding model selection (dual strategy)
- [x] ADR-004: Authentication (Azure AD OIDC)
- [x] ADR-005: LLM abstraction layer
- [x] Glossary of medical coding and project terms
- [x] Product vision document
- [x] Coding conventions document
- [x] Project structure rules

### In Progress
- [ ] Set up Python project (pyproject.toml, ruff, mypy, pytest)
- [ ] Set up Next.js frontend project scaffold
- [ ] Docker Compose for local development (Postgres, Qdrant, API)
- [ ] Create CLAUDE.md with codebase context for AI-assisted development

### Not Started
- [ ] CI/CD pipeline skeleton (GitHub Actions)
- [ ] Pre-commit hooks (ruff, mypy, eslint, prettier)
- [ ] Environment variable schema and .env.example
- [ ] Local development setup documentation

## Phase 2: Data Ingestion Pipeline

### Not Started
- [ ] ICD-10-CM XML parser for tabular list (`icd10c-tabular-April-1-2026.xml`)
  - Parse chapter > section > category > subcategory > code hierarchy
  - Extract includes, excludes1, excludes2, code_first, use_additional, code_also
  - Extract 7th character definitions and applicability
  - Handle addenda (additions, revisions, deletions)
- [ ] ICD-10-CM XML parser for alphabetic index (`icd10cm-index-April-1-2026-XML.xml`)
  - Parse main terms, subterms, and see/see-also references
  - Resolve code references to tabular entries
- [ ] ICD-10-CM XML parser for drug table (`icd10cm-drug-April-1-2026-XML.xml`)
  - Parse substance names and intent columns
  - Map to poisoning, adverse effect, and underdosing codes
- [ ] ICD-10-CM XML parser for neoplasm table (`icd10cm-neoplasm-April-1-2026-XML.xml`)
  - Parse anatomical sites and behavior columns
  - Map to malignant, benign, uncertain, and unspecified codes
- [ ] ICD-10-CM XML parser for external cause index (`icd10cm-eindex-April-1-2026-XML.xml`)
- [ ] Chunk builder: assemble code-centric chunks with inherited context (ADR-002)
  - Walk hierarchy upward for each billable code
  - Concatenate inherited excludes, includes, instructions
  - Generate structured chunk text for embedding
- [ ] Embedding pipeline: OpenAI text-embedding-3-large for descriptions
- [ ] Embedding pipeline: PubMedBERT for clinical context
- [ ] BM25 sparse vector computation
- [ ] Qdrant collection creation and schema setup
- [ ] Qdrant batch upsert with named vectors + payloads
- [ ] Ingestion pipeline orchestrator (end-to-end: XML -> chunks -> embeddings -> Qdrant)
- [ ] Ingestion validation: verify chunk counts, vector dimensions, payload integrity
- [ ] Content hash caching for incremental re-embedding on updates
- [ ] Unit tests for XML parsers (test against known code structures)
- [ ] Integration test for full ingestion pipeline

## Phase 3: RAG Pipeline + Backend Core

### Not Started
- [ ] FastAPI application skeleton with async support
- [ ] LLM abstraction layer (ABC, Factory, providers) per ADR-005
  - Anthropic Claude provider implementation
  - OpenAI GPT provider implementation
  - Mock provider for testing
- [ ] System prompt engineering with negative prompting
- [ ] Retrieval pipeline:
  - Query embedding (OpenAI + PubMedBERT)
  - Qdrant multi-vector search (description + clinical_context + sparse)
  - Payload filtering (chapter, billable, code_type)
  - Reciprocal Rank Fusion
  - Top-K selection with confidence threshold
- [ ] LLM generation pipeline:
  - Context formatting for LLM input
  - Structured output parsing (CodingResult model)
  - Output validation (code existence, format, billable status)
  - Excludes1 cross-check
  - Hallucination detection and filtering
- [ ] Coding recommendation endpoint (`POST /api/v1/code`)
- [ ] Streaming response endpoint (`POST /api/v1/code/stream`)
- [ ] Code detail lookup endpoint (`GET /api/v1/codes/{code}`)
- [ ] Search endpoint for direct code search (`GET /api/v1/codes/search`)
- [ ] Health check endpoint (`GET /api/v1/health`)
- [ ] Request/response logging middleware
- [ ] Rate limiting middleware
- [ ] Error handling and structured error responses
- [ ] Unit tests for retrieval pipeline
- [ ] Unit tests for LLM output validation
- [ ] Integration tests for RAG pipeline (mock LLM, real Qdrant)

## Phase 4: Database, Auth, Multi-Tenancy

### Not Started
- [ ] PostgreSQL schema design:
  - `tenants` table (id, name, slug, azure_tenant_id, settings, created_at)
  - `users` table (id, tenant_id, email, display_name, roles, created_at)
  - `sessions` table (id, user_id, tenant_id, refresh_token_hash, device, expires_at)
  - `coding_sessions` table (id, user_id, tenant_id, query, result, chunks_used, created_at)
  - `feedback` table (id, coding_session_id, rating, correction, notes, created_at)
  - `auth_audit_log` table (id, user_id, tenant_id, event, ip, user_agent, created_at)
  - `tenant_settings` table (tenant_id, llm_provider, llm_model, custom_prompt, etc.)
  - `tenant_role_mappings` table (tenant_id, azure_group_id, autocode_role)
- [ ] Alembic migration setup and initial migration
- [ ] Row-level security policies on all tenant-scoped tables
- [ ] Azure AD OIDC integration per ADR-004:
  - OIDC discovery and PKCE flow
  - Token exchange and id_token validation
  - Auto Code JWT issuance (access + refresh tokens)
  - Refresh token rotation
  - Session management and revocation
- [ ] FastAPI authentication middleware (`get_current_user` dependency)
- [ ] Tenant context injection middleware
- [ ] Role-based access control decorator/dependency
- [ ] User management endpoints (admin: list, invite, deactivate)
- [ ] Tenant settings endpoints (admin: configure LLM, roles, etc.)
- [ ] Audit log query endpoint (admin)
- [ ] Unit tests for auth flow
- [ ] Integration tests for multi-tenant isolation

## Phase 5: Frontend

### Not Started
- [ ] Next.js App Router project setup (TypeScript, Tailwind CSS, shadcn/ui)
- [ ] Authentication flow (login page, OIDC redirect, token storage)
- [ ] Layout: sidebar navigation, header with user/tenant info
- [ ] Coding assistant page:
  - Clinical description input (textarea with character count)
  - Submit button with loading state
  - Streaming response display
  - Code recommendation cards (code, description, confidence, reasoning)
  - Warning badges (Excludes1 conflicts, Code First reminders)
  - Copy-to-clipboard for individual codes
  - "Add all to session" action
- [ ] Code detail modal/panel:
  - Full code description and context
  - Hierarchy breadcrumb (chapter > section > category > code)
  - Excludes1/Excludes2 lists with clickable code links
  - Coding instructions (Code First, Use Additional, Code Also)
  - 7th character selector (if applicable)
- [ ] Search page:
  - Code search by code identifier or description
  - Filters (chapter, billable, code type)
  - Results table with pagination
- [ ] History page:
  - List of past coding sessions
  - Click to view session details and results
  - Feedback submission (thumbs up/down, correction, notes)
- [ ] Settings page (admin):
  - LLM provider and model selection
  - User management table
  - Role mapping configuration
  - Audit log viewer
- [ ] Responsive design (desktop primary, tablet secondary)
- [ ] Dark mode support
- [ ] Accessibility audit (WCAG 2.1 AA)
- [ ] Component unit tests (Vitest + React Testing Library)
- [ ] E2E tests (Playwright)

## Phase 6: Export + Polish

### Not Started
- [ ] Export coding session results as CSV
- [ ] Export coding session results as PDF report
- [ ] Export coding session results as JSON (FHIR-compatible structure)
- [ ] Batch coding: upload CSV of clinical descriptions, process in bulk
- [ ] Keyboard shortcuts for common actions
- [ ] Loading skeletons and optimistic UI updates
- [ ] Error boundaries and graceful degradation
- [ ] Toast notifications for actions
- [ ] Session timeout warning and auto-refresh

## Phase 7: Infrastructure + Deployment

### Not Started
- [ ] Dockerfile for FastAPI backend (multi-stage build)
- [ ] Dockerfile for Next.js frontend
- [ ] Docker Compose for production-like local setup
- [ ] Terraform modules:
  - Azure Container Apps (or AKS) for API + frontend
  - Azure Database for PostgreSQL Flexible Server
  - Azure Container Instance for Qdrant (or VM with persistent disk)
  - Azure Key Vault for secrets
  - Azure Monitor for logging and alerting
  - Azure Front Door / Application Gateway for SSL termination
- [ ] GitHub Actions CI pipeline:
  - Lint (ruff, mypy, eslint, prettier)
  - Unit tests (pytest, vitest)
  - Integration tests
  - Docker image build and push
  - Security scanning (Trivy, Bandit)
- [ ] GitHub Actions CD pipeline:
  - Staging deployment on PR merge to `develop`
  - Production deployment on release tag
  - Database migration execution
  - Qdrant collection verification
- [ ] Monitoring and alerting:
  - API latency and error rate dashboards
  - Qdrant health and query latency
  - LLM API cost tracking
  - Authentication failure alerts
- [ ] Backup strategy:
  - PostgreSQL daily backups with 30-day retention
  - Qdrant snapshots before/after ingestion
- [ ] SSL/TLS configuration
- [ ] DNS and domain setup

## Phase 8: Testing + Security

### Not Started
- [ ] Security review:
  - OWASP Top 10 assessment
  - Authentication flow security audit
  - Input sanitization (clinical description input, search queries)
  - SQL injection prevention verification
  - XSS prevention verification
  - CORS configuration review
  - Rate limiting effectiveness
  - JWT security (algorithm, expiry, rotation)
- [ ] HIPAA compliance checklist:
  - PHI inventory (what data, where stored, who accesses)
  - Encryption at rest (PostgreSQL, Qdrant, backups)
  - Encryption in transit (TLS 1.3 everywhere)
  - Access controls and audit logging
  - Breach notification procedures
  - BAA template preparation
- [ ] Performance testing:
  - API load testing (target: 100 concurrent users)
  - Qdrant query latency benchmarking (target: p95 < 200ms)
  - LLM response latency benchmarking (target: p95 < 5s)
  - Frontend Lighthouse audit (target: 90+ all categories)
- [ ] Penetration testing (external)
- [ ] Disaster recovery drill
- [ ] Data retention policy implementation
