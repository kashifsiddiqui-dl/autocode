# Auto Code - Product Roadmap

## Timeline Overview

| Phase | Name | Duration | Target Start | Target End | Dependencies |
|---|---|---|---|---|---|
| 1 | Foundation & Documentation | 1 week | Week 1 | Week 1 | None |
| 2 | Data Ingestion Pipeline | 2 weeks | Week 2 | Week 3 | Phase 1 |
| 3 | RAG Pipeline + Backend Core | 2 weeks | Week 4 | Week 5 | Phase 2 |
| 4 | Database, Auth, Multi-Tenancy | 2 weeks | Week 4 | Week 5 | Phase 1 (parallel with Phase 3) |
| 5 | Frontend | 3 weeks | Week 6 | Week 8 | Phase 3, Phase 4 |
| 6 | Export + Polish | 1 week | Week 9 | Week 9 | Phase 5 |
| 7 | Infrastructure + Deployment | 2 weeks | Week 8 | Week 9 | Phase 3, Phase 4 (overlaps with Phase 5/6) |
| 8 | Testing + Security | 2 weeks | Week 10 | Week 11 | All phases |
| | **Total** | **~11 weeks** | | | |

## Phase 1: Foundation & Documentation (Week 1)

**Goal:** Establish project structure, tooling, architecture decisions, and development environment so all subsequent work builds on a solid foundation.

**Deliverables:**
- Architecture Decision Records (ADRs 001-005)
- Project scaffolding (Python backend, Next.js frontend)
- Docker Compose for local development
- CI/CD pipeline skeleton
- Coding conventions and project structure documentation

**Exit Criteria:**
- `docker compose up` starts PostgreSQL, Qdrant, and API containers
- Ruff, mypy, eslint, prettier all pass on empty projects
- All ADRs reviewed and accepted

**Risks:**
- Low risk. Primarily documentation and configuration.

---

## Phase 2: Data Ingestion Pipeline (Weeks 2-3)

**Goal:** Parse ICD-10-CM April 2026 XML files, build code-centric chunks, generate embeddings, and load them into Qdrant.

**Deliverables:**
- XML parsers for all five source types (tabular, index, drug, neoplasm, e-index)
- Chunk builder with hierarchical context inheritance
- Embedding pipeline (OpenAI + PubMedBERT + BM25)
- Qdrant collection with ~130K populated points
- Ingestion validation and reporting

**Key Metrics:**
- ~74K billable code chunks with full inherited context
- ~50K index entry chunks
- ~5K drug + neoplasm + e-index chunks
- All chunks have 3 vectors (description 1024d, clinical_context 768d, sparse)
- Ingestion completes in under 60 minutes (target: 30 min)

**Dependencies:**
- Phase 1 (Docker Compose with Qdrant running)
- OpenAI API key for description embeddings
- PubMedBERT model downloaded

**Risks:**
- XML parsing edge cases (malformed entries, special characters in code descriptions)
- PubMedBERT 512-token limit may truncate long clinical context texts. Mitigation: chunking long context into overlapping windows and mean-pooling embeddings.
- OpenAI API rate limits during batch embedding. Mitigation: batch requests with exponential backoff.

---

## Phase 3: RAG Pipeline + Backend Core (Weeks 4-5)

**Goal:** Build the core FastAPI application with the retrieval pipeline, LLM integration, and coding recommendation API.

**Deliverables:**
- FastAPI application with async endpoints
- LLM abstraction layer (Anthropic + OpenAI providers)
- Multi-vector retrieval with RRF fusion
- System prompt with negative prompting
- Output validation and hallucination detection
- Core API endpoints (code, stream, search, health)

**Key Metrics:**
- Retrieval accuracy: relevant code in top-5 results for >90% of test queries
- End-to-end latency: < 5 seconds for non-streaming, first token < 1s for streaming
- Hallucination rate: < 1% (codes in response not present in retrieved context)

**Dependencies:**
- Phase 2 (populated Qdrant collection)
- Anthropic API key, OpenAI API key

**Risks:**
- Retrieval quality may require tuning of RRF weights, search top-K, and confidence thresholds. Plan for iterative tuning with a test query set.
- LLM prompt engineering may require multiple iterations to achieve consistent structured output across both Claude and GPT.

---

## Phase 4: Database, Auth, Multi-Tenancy (Weeks 4-5, parallel with Phase 3)

**Goal:** Implement PostgreSQL schema, Azure AD OIDC authentication, and multi-tenant data isolation.

**Deliverables:**
- PostgreSQL schema with all tables
- Alembic migrations
- Row-level security policies
- Azure AD OIDC authentication flow
- JWT-based session management
- Tenant context injection middleware
- Role-based access control

**Dependencies:**
- Phase 1 (Docker Compose with PostgreSQL)
- Azure AD tenant for development (test app registration)

**Risks:**
- Azure AD app registration configuration can be fiddly. Document the exact steps.
- RLS policies must be thoroughly tested to prevent cross-tenant data leakage. Dedicate time for multi-tenant isolation tests.
- Refresh token rotation logic is subtle. Edge cases: concurrent requests with the same refresh token, clock skew.

---

## Phase 5: Frontend (Weeks 6-8)

**Goal:** Build the Next.js frontend with the coding assistant UI, search, history, and admin settings.

**Deliverables:**
- Authentication flow (login, redirect, token management)
- Coding assistant page with streaming response
- Code recommendation cards with confidence and warnings
- Code detail view with full context
- Search page with filters
- History page with feedback submission
- Admin settings page
- Responsive layout with dark mode

**Dependencies:**
- Phase 3 (API endpoints to call)
- Phase 4 (Authentication endpoints)

**Risks:**
- Streaming response rendering (SSE) can be tricky with Next.js App Router and React Suspense. Prototype early.
- Code detail view has complex nested data (hierarchy, excludes, 7th char). Plan the component hierarchy carefully.
- Accessibility in complex interactive components (modals, dropdowns, streaming text) requires attention.

---

## Phase 6: Export + Polish (Week 9)

**Goal:** Add export capabilities and polish the user experience.

**Deliverables:**
- CSV, PDF, and JSON export for coding sessions
- Batch coding (CSV upload)
- Keyboard shortcuts
- Loading states and error handling improvements
- Toast notifications

**Dependencies:**
- Phase 5 (frontend to add features to)

**Risks:**
- PDF generation can be complex. Consider a server-side PDF library (weasyprint or reportlab).
- Batch coding needs queue management for large CSV files. May need background task processing (Celery/ARQ).

---

## Phase 7: Infrastructure + Deployment (Weeks 8-9, overlapping with Phase 5/6)

**Goal:** Containerize, provision cloud infrastructure, and establish CI/CD pipelines.

**Deliverables:**
- Production Dockerfiles (multi-stage builds)
- Terraform modules for Azure infrastructure
- CI pipeline (lint, test, build, scan)
- CD pipeline (staging on merge, production on release)
- Monitoring dashboards and alerting
- Backup automation

**Dependencies:**
- Phase 3, Phase 4 (applications to deploy)
- Azure subscription with appropriate permissions

**Risks:**
- Qdrant hosting on Azure requires careful planning (persistent disk, memory allocation). Azure Container Apps may not provide sufficient control; may need a dedicated VM or AKS.
- Terraform state management and secrets handling. Use Azure Storage for state backend, Key Vault for secrets.
- Database migrations in CD pipeline need to handle rollback scenarios.

---

## Phase 8: Testing + Security (Weeks 10-11)

**Goal:** Comprehensive security review, HIPAA compliance verification, performance testing, and hardening.

**Deliverables:**
- Security audit report (OWASP Top 10)
- HIPAA compliance checklist (completed)
- Performance test results and optimizations
- Penetration test report (if external testing engaged)
- Disaster recovery runbook

**Dependencies:**
- All prior phases (full system running in staging)

**Risks:**
- Security findings may require architectural changes. Mitigated by security-conscious design in earlier phases.
- Performance testing may reveal Qdrant or LLM latency bottlenecks under load. Plan for query optimization and caching.

---

## Post-Launch Roadmap (Future)

### Q3 2026
- ICD-10-CM October 2026 update ingestion
- Fine-tuned embedding model using production query-result feedback
- CPT code support (requires AMA license)
- EMR integration exploration (Epic FHIR, Cerner)

### Q4 2026
- HCPCS code support
- Multi-language support (ICD-10 is multilingual)
- Advanced analytics dashboard (coding patterns, common queries, accuracy trends)
- Mobile-responsive progressive web app

### 2027
- ICD-10-PCS (procedure codes) support
- AI-assisted code auditing (review existing code assignments)
- Batch processing at scale (thousands of records)
- On-premise deployment option for high-security customers
- SOC 2 Type II certification
