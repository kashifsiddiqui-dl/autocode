# Auto Code - Technology Stack Decisions

This document records every technology choice for the Auto Code platform, including version constraints, justifications, and alternatives considered. Changes to this document require an ADR in `decisions/`.

---

## Frontend

### Next.js 15 (App Router)

**Version**: `>=15.0.0 <16.0.0`

**Why**: Next.js 15 with the App Router provides React Server Components, streaming SSR, and a file-system-based routing model that simplifies the frontend architecture. Server Components reduce client-side JavaScript by keeping data-fetching and rendering on the server, which improves performance for the data-heavy coding results UI.

**Why not alternatives**:
- *Remix*: Strong contender for data loading patterns, but smaller ecosystem and less corporate adoption for healthcare SaaS. Next.js has a larger community for hiring and support.
- *Vite + React Router*: No SSR out of the box. Would require more custom infrastructure for SEO (login/marketing pages) and initial load performance.
- *Angular*: Heavier framework with steeper learning curve. React ecosystem has better component library options (shadcn/ui).

### React 19

**Version**: `>=19.0.0 <20.0.0`

**Why**: React 19 introduces Actions, `useActionState`, `useOptimistic`, and the `use()` hook, which simplify form handling and async data patterns that are central to the coding workflow (submit clinical note, display results, provide feedback). Server Components support (via Next.js) is also a React 19 feature.

### TypeScript 5.x

**Version**: `>=5.4.0 <6.0.0`

**Why**: Type safety is non-negotiable for a healthcare application. TypeScript catches entire categories of bugs at compile time. Version 5.x provides improved type inference, `satisfies` operator, and const type parameters.

**Why not JavaScript**: Unacceptable risk for a HIPAA-regulated application. Type errors in API response handling could lead to incorrect code display.

### Tailwind CSS

**Version**: `>=3.4.0 <5.0.0`

**Why**: Utility-first CSS that co-locates styles with markup, eliminating CSS naming conflicts and dead code. Works seamlessly with shadcn/ui. The design-token approach (via `tailwind.config`) ensures visual consistency across the application.

**Why not alternatives**:
- *CSS Modules*: More boilerplate, harder to maintain consistency without a design system.
- *styled-components*: Runtime CSS-in-JS adds bundle size and performance overhead. Not compatible with React Server Components.

### shadcn/ui

**Version**: Latest (copy-paste component library, not a versioned dependency)

**Why**: Accessible, well-designed React components built on Radix UI primitives and styled with Tailwind CSS. Unlike traditional component libraries, shadcn/ui components are copied into the project, giving full ownership and customization without version lock-in. Meets WCAG 2.1 AA accessibility requirements.

**Why not alternatives**:
- *MUI (Material UI)*: Opinionated design language (Material Design) that is harder to customize to a medical/professional aesthetic. Heavier bundle.
- *Ant Design*: Designed for Chinese market defaults. Customization is possible but less natural than Tailwind-based approaches.
- *Chakra UI*: Good accessibility but runtime CSS-in-JS (same issue as styled-components with RSC).

### Zustand

**Version**: `>=4.5.0 <6.0.0`

**Why**: Lightweight client-side state management for UI state that does not belong in server state (e.g., sidebar open/close, active filters, user preferences). Zustand has a minimal API, no boilerplate, and works well with React 19.

**Why not alternatives**:
- *Redux Toolkit*: Overkill for the client state needs. Most "state" in this application is server state handled by TanStack Query.
- *Jotai/Recoil*: Atomic state model is powerful but adds conceptual overhead for a small client state surface.
- *React Context*: Causes unnecessary re-renders without careful memoization. Not suitable for frequently-changing state.

### TanStack Query (React Query)

**Version**: `>=5.0.0 <6.0.0`

**Why**: Server state management with caching, background refetching, optimistic updates, and pagination. The coding results workflow requires polling for async job completion, cache invalidation when new notes are submitted, and optimistic UI updates for user feedback on code suggestions. TanStack Query handles all of these patterns.

**Why not alternatives**:
- *SWR*: Simpler but lacks mutation support, optimistic updates, and the query invalidation model needed for complex workflows.
- *RTK Query*: Tied to Redux. Unnecessary if not using Redux for client state.

---

## Backend

### FastAPI

**Version**: `>=0.110.0`

**Why**: High-performance async Python web framework with automatic OpenAPI documentation, Pydantic integration for request/response validation, and dependency injection. The auto-generated OpenAPI spec is critical for API-first development and TypeScript client generation. FastAPI's async support is essential for the I/O-heavy RAG pipeline (concurrent database, vector DB, and LLM API calls).

**Why not alternatives**:
- *Django REST Framework*: Synchronous by default. Django's ORM is not async-first. The admin panel is unnecessary for a SaaS API.
- *Flask*: No async support, no built-in validation, no auto-generated API docs. Would require assembling many libraries.
- *Node.js (Express/Fastify)*: Python has a much stronger ecosystem for ML/NLP (embedding models, rerankers, clinical NLP). The RAG pipeline benefits from Python libraries.

### Python 3.12+

**Version**: `>=3.12.0`

**Why**: Python 3.12 provides significant performance improvements (up to 5% faster), improved error messages, `type` statement for type aliases, and better typing support (`TypeVar` defaults, `@override` decorator). The ML/NLP ecosystem (transformers, sentence-transformers, qdrant-client) is Python-native.

### SQLAlchemy 2.0 (Async)

**Version**: `>=2.0.0 <3.0.0`

**Why**: SQLAlchemy 2.0 provides a modern, type-safe ORM with native async support via `asyncpg`. The `mapped_column` and `DeclarativeBase` patterns reduce boilerplate while maintaining full type safety. Relationship loading strategies (selectinload, joinedload) enable efficient query patterns for the hierarchical ICD-10-CM data model.

**Why not alternatives**:
- *Tortoise ORM*: Less mature, smaller community, fewer migration tools.
- *SQLModel*: Built on SQLAlchemy but adds Pydantic integration that sometimes conflicts with SQLAlchemy's own patterns. Less control over advanced features.
- *Raw SQL / asyncpg*: Maximum performance but no ORM benefits (migration generation, relationship management, query building). Maintenance burden too high.

### Alembic

**Version**: `>=1.13.0`

**Why**: The de facto migration tool for SQLAlchemy. Auto-generates migrations from model changes, supports branching and merging, and integrates with the async SQLAlchemy engine. Critical for managing schema changes across multi-tenant PostgreSQL with RLS policies.

### Pydantic v2

**Version**: `>=2.5.0 <3.0.0`

**Why**: Pydantic v2 is a ground-up Rust-powered rewrite that is 5-20x faster than v1. It provides strict validation, serialization, and JSON Schema generation. FastAPI's native integration means request/response validation is automatic. The `model_validator` and `field_validator` patterns provide powerful custom validation for medical coding inputs.

**Important**: Always use v2 syntax (`model_validator`, `field_validator`, `model_config`). Never use deprecated v1 patterns (`validator`, `Config` inner class).

---

## Databases

### PostgreSQL 17 (AWS RDS)

**Version**: `17.x`

**Why**: PostgreSQL is the most capable open-source relational database. Version 17 provides improved vacuum performance, enhanced JSON capabilities, and incremental backup support. AWS RDS provides managed operations with encryption at rest (KMS), automated backups, Multi-AZ deployment for high availability, and read replicas for scaling.

**Key configuration**:
- Encryption at rest via AWS KMS (AES-256) - HIPAA requirement
- Multi-AZ deployment for production - high availability
- Automated backups with 35-day retention
- Row-Level Security (RLS) for multi-tenant isolation
- Connection pooling via PgBouncer or RDS Proxy
- `pgvector` extension NOT used (Qdrant handles vector search)

**Why not alternatives**:
- *MySQL/MariaDB*: No native RLS support. JSON capabilities are less mature. Window functions and CTEs are less powerful for hierarchical ICD-10-CM data queries.
- *Aurora PostgreSQL*: Viable but more expensive. Standard RDS PostgreSQL is sufficient for current scale projections.
- *CockroachDB*: Distributed SQL is overkill for current scale. Higher operational complexity.

### Qdrant (Self-Hosted)

**Version**: `>=1.9.0`

**Why**: Qdrant is a purpose-built vector database that supports named vectors (allowing dense + sparse vectors in a single point), payload filtering (for metadata-based filtering), and hybrid search. These features are critical for the 4-stage RAG pipeline. Self-hosting provides data sovereignty control required for HIPAA compliance.

**Key configuration**:
- Named vectors: `dense` (text-embedding-3-large, 1024d) and `sparse` (BM25 via SPLADE or custom)
- Collection per coding standard (e.g., `icd10cm_april_2026`)
- Payload indexes on: `chapter`, `block`, `category`, `code`, `valid_from`, `valid_to`, `tenant_id`
- WAL-based persistence with encrypted volumes
- Snapshots for backup and disaster recovery

**Why not alternatives**:
- *Pinecone*: Managed service with excellent developer experience, but data leaves your infrastructure. HIPAA BAA available but adds third-party risk. No named vectors for hybrid search.
- *Weaviate*: Capable but heavier (includes its own ML model serving). Named vectors support is newer and less mature.
- *pgvector*: Embedding search within PostgreSQL is convenient but lacks hybrid search, named vectors, and the performance characteristics of a dedicated vector database at scale. HNSW index in pgvector is less tunable than Qdrant's.
- *Milvus*: Powerful but operationally complex (depends on etcd, MinIO, Pulsar). Overkill for current deployment model.
- *ChromaDB*: Not production-ready. No persistence guarantees, no named vectors, limited filtering.

---

## AI / ML

### OpenAI text-embedding-3-large (Dense Embeddings)

**Dimensions**: 1024 (reduced from native 3072 via Matryoshka representation)

**Why**: OpenAI's latest embedding model provides state-of-the-art retrieval quality. The Matryoshka representation allows dimension reduction from 3072 to 1024 with minimal quality loss, reducing storage and compute costs by ~66%. The model handles medical terminology well out of the box.

**Why not alternatives**:
- *text-embedding-3-small*: Lower quality for medical terminology. The cost savings are not significant enough to justify reduced retrieval accuracy in a patient-safety-critical application.
- *Cohere embed-v3*: Competitive quality but adds another vendor dependency. OpenAI embedding + Anthropic/OpenAI LLM is a simpler vendor matrix.
- *Self-hosted models (e5-large, BGE)*: Good quality but requires GPU infrastructure for inference. The operational overhead is not justified when a managed API provides equivalent or better quality.

### PubMedBERT (Clinical Context Embeddings)

**Why**: PubMedBERT is pre-trained on biomedical literature and understands clinical terminology, abbreviations, and medical context that general-purpose embedding models may miss. Used as a secondary signal during the metadata filtering and reranking stages, not as the primary retrieval embedding.

**Why not alternatives**:
- *ClinicalBERT*: Trained on clinical notes (MIMIC-III) which is closer to input data, but has restrictive licensing for commercial use.
- *BioBERT*: PubMedBERT outperforms BioBERT on biomedical NLP benchmarks.

### BAAI/bge-reranker-v2-m3 (Cross-Encoder Reranker)

**Why**: Cross-encoder reranking significantly improves retrieval precision by jointly encoding the query and each candidate. BGE-reranker-v2-m3 is multilingual, high-quality, and runs efficiently on CPU for the small candidate sets (top-50 to top-100) produced by the initial retrieval stage.

**Why not alternatives**:
- *Cohere Rerank*: Managed API that adds latency and another vendor. Self-hosted reranking is faster and keeps data on-premises.
- *ColBERT*: Late interaction model that is fast but requires more complex indexing infrastructure.
- *No reranking*: Unacceptable. Hybrid search (dense + sparse) produces a merged candidate set that benefits significantly from reranking. Clinical coding accuracy depends on precise ranking.

### Anthropic Claude / OpenAI GPT (LLM - Configurable)

**Version**: Anthropic Claude (claude-sonnet-4-20250514 default), OpenAI GPT-4o (fallback)

**Why**: The LLM is used for reasoning over retrieved ICD-10-CM context to assign codes, not as a knowledge source. Claude's large context window (200K tokens) accommodates the expanded hierarchy context. Configurability per tenant allows organizations to choose their preferred provider based on their own BAA and compliance requirements.

**Why configurable**:
- Some organizations have existing BAAs with OpenAI but not Anthropic, or vice versa
- Model performance varies by clinical specialty; tenants may prefer one for their use case
- Provider outages can be mitigated by failover to the alternate provider
- Cost optimization: different models have different price/performance trade-offs

**Why not alternatives**:
- *Self-hosted LLM (Llama, Mistral)*: Current open-source models do not match Claude/GPT-4o quality for complex medical reasoning. The cost of GPU infrastructure and model serving outweighs API costs at current scale.
- *Google Gemini*: Viable but adds another cloud vendor. Google Cloud BAA and HIPAA story is strong but most healthcare organizations are already on AWS or Azure.

---

## Authentication & Authorization

### Azure AD / Entra ID (OIDC)

**Why**: Most healthcare organizations use Microsoft 365 and Azure AD for identity. OIDC SSO integration means users authenticate with their existing corporate credentials. No passwords are stored in Auto Code. Azure AD provides MFA, conditional access policies, and group-based role assignment that map directly to RBAC needs.

**Key configuration**:
- OIDC Authorization Code Flow with PKCE (for the web frontend)
- Client Credentials Flow (for service-to-service / EMR integration)
- JWT validation with Azure AD's JWKS endpoint
- Group claims mapped to application roles (Admin, Coder, Reviewer, ReadOnly)
- Tenant claim used to set PostgreSQL RLS context

**Libraries**:
- `authlib>=1.3.0` - OIDC client and JWT handling
- `python-jose>=3.3.0` - JWT validation and claims extraction

**Why not alternatives**:
- *Auth0*: Excellent developer experience but adds cost and another vendor for healthcare organizations that already have Azure AD.
- *Keycloak*: Self-hosted identity provider adds operational burden. Healthcare organizations do not want to manage another identity system.
- *Cognito*: AWS-native but less common in healthcare enterprise environments than Azure AD. Would fragment the identity story across Azure (corporate) and AWS (application).
- *Local auth (username/password)*: Unacceptable for HIPAA compliance and enterprise healthcare. SSO is a hard requirement.

---

## Infrastructure

### AWS

**Services used**:

| Service | Purpose | Configuration |
|---------|---------|---------------|
| EC2 | Application servers (backend + Qdrant) | t3.xlarge (backend), r6i.xlarge (Qdrant), Auto Scaling Groups |
| RDS | PostgreSQL 17 | db.r6g.large, Multi-AZ, encrypted, 35-day backup retention |
| ALB | Load balancer + TLS termination | HTTPS only, WAF integration, health checks |
| S3 | Qdrant snapshots, Terraform state, static assets | Encrypted, versioned, lifecycle policies |
| KMS | Encryption key management | Customer-managed keys for RDS, S3, EBS |
| WAF | Web application firewall | OWASP Top 10 rules, rate limiting, geo-blocking |
| CloudWatch | Logging and basic monitoring | Log groups with encryption, metric alarms |
| Route53 | DNS | Health-checked records, failover routing |
| Secrets Manager | Secret storage | Database credentials, API keys, OIDC secrets |
| VPC | Network isolation | Public/private subnets, NAT gateways, security groups |

**Why AWS over alternatives**:
- *Azure*: Strong healthcare presence, but the application team's expertise is AWS. Azure AD is used for identity only (OIDC is protocol-level, not infrastructure-level).
- *GCP*: Less common in healthcare enterprise. HIPAA BAA coverage is narrower than AWS.

### Terraform

**Version**: `>=1.7.0`

**Why**: Infrastructure as code for reproducible, version-controlled environments. Terraform's declarative model and state management are well-suited for the multi-environment (dev, staging, production) deployment model. AWS provider is the most mature.

**Why not alternatives**:
- *CloudFormation*: AWS-only, verbose YAML/JSON, slower development cycle. Terraform HCL is more readable and productive.
- *Pulumi*: General-purpose programming languages for IaC is powerful but adds complexity. The infrastructure is relatively straightforward and benefits from Terraform's declarative constraints.
- *CDK*: Generates CloudFormation under the hood, with the same limitations. TypeScript CDK is appealing but debugging synthesized CloudFormation is painful.

### Docker

**Version**: Docker Engine `>=24.0`, Docker Compose `>=2.20`

**Why**: Containerization for consistent development and deployment environments. Docker Compose enables the full local development stack (PostgreSQL, Qdrant, backend, frontend) with a single command. Production containers use multi-stage builds for minimal image size and attack surface.

**Container guidelines**:
- Multi-stage builds (builder + runtime)
- Non-root user execution
- Read-only root filesystem where possible
- Minimal base images (python:3.12-slim, node:20-alpine)
- No secrets in images (use runtime environment variables or Secrets Manager)

---

## CI/CD

### GitHub Actions

**Why**: Native integration with GitHub (where the code is hosted). Matrix builds for testing across Python versions, parallel test execution, and caching reduce CI time. GitHub's OIDC integration with AWS enables secure, keyless deployments.

**Pipeline stages**:
1. **Lint**: ruff check, mypy, ESLint, Prettier check
2. **Test**: pytest (unit + integration with testcontainers), Vitest
3. **Security**: dependency scanning, SAST (Bandit/Semgrep), container scanning
4. **Build**: Docker images, Next.js static optimization
5. **Deploy**: Terraform plan (PR), Terraform apply (merge to main), rolling deployment

**Why not alternatives**:
- *Jenkins*: Self-hosted operational burden. GitHub Actions is managed and sufficient.
- *GitLab CI*: Would require migrating to GitLab. GitHub Actions is equivalent for the pipeline needs.
- *CircleCI*: Good product but another vendor to manage. GitHub Actions integration is tighter.

---

## Testing

### pytest + pytest-asyncio

**Version**: `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`

**Why**: pytest is the standard Python testing framework. pytest-asyncio enables testing async FastAPI endpoints and async database operations. Fixture-based test setup keeps tests clean and composable.

### testcontainers

**Version**: `testcontainers>=4.0.0`

**Why**: Spin up real PostgreSQL and Qdrant instances in Docker containers for integration tests. Tests run against real databases, not mocks, catching issues that unit tests miss (SQL syntax, RLS policies, vector search behavior).

### Vitest

**Version**: `>=1.6.0`

**Why**: Fast, Vite-native test runner for React component and utility testing. Jest-compatible API with better performance and ESM support. Works seamlessly with the Next.js/TypeScript toolchain.

### Playwright

**Version**: `>=1.42.0`

**Why**: Cross-browser end-to-end testing that covers the full user workflow (login via SSO mock, submit clinical note, review coding results, provide feedback). Playwright's auto-wait and network interception features make tests reliable.

---

## Monitoring & Observability

### CloudWatch

**Why**: Native AWS integration for logs, metrics, and alarms. All application logs ship to CloudWatch Log Groups with encryption. Basic operational alarms (CPU, memory, error rates, latency percentiles) trigger SNS notifications.

### Prometheus + Grafana

**Why**: Application-level metrics (RAG pipeline latency per stage, embedding generation time, reranker latency, LLM response time, cache hit rates, codes per request) require more granular instrumentation than CloudWatch provides. Prometheus scrapes metrics from the FastAPI application, and Grafana provides dashboards and alerting.

**Key metrics tracked**:
- RAG pipeline end-to-end latency (p50, p95, p99)
- Per-stage latency (retrieval, filtering, reranking, hierarchy expansion, LLM)
- Embedding generation throughput
- Qdrant query latency and recall
- LLM token usage per request
- Code assignment confidence distribution
- Error rates by type and tenant
- Active users and concurrent coding sessions per tenant

**Why not alternatives**:
- *Datadog*: Excellent product but expensive at scale. The combination of CloudWatch (infrastructure) + Prometheus/Grafana (application) provides equivalent observability at lower cost.
- *New Relic*: Similar cost concerns. The team has more experience with Prometheus/Grafana.
- *OpenTelemetry + Jaeger*: Planned for distributed tracing in a future phase. Not a replacement for metrics and dashboards.

---

## Version Pinning Policy

- **Major versions**: Pinned with upper bound (e.g., `>=15.0.0 <16.0.0`). Major upgrades require an ADR.
- **Minor versions**: Minimum version specified (e.g., `>=2.5.0`). Minor upgrades are allowed after testing.
- **Patch versions**: Not pinned. Patch updates are applied automatically by Dependabot.
- **Lock files**: `package-lock.json` (frontend) and `uv.lock` or `poetry.lock` (backend) are committed and used for reproducible builds.
- **Security patches**: Applied within 48 hours for critical vulnerabilities, regardless of version policy.
