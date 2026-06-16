# Auto Code - Project Constitution

These are the immutable principles that govern the Auto Code project. They are non-negotiable and must be upheld in every design decision, code change, and operational procedure. Any proposed change that conflicts with these principles must be rejected or the constitution must be formally amended first.

---

## 1. Patient Safety First

Medical coding accuracy is paramount. An incorrect ICD-10-CM code can lead to denied insurance claims, delayed treatment, incorrect medical records, and downstream harm to patients. Every design decision must prioritize coding accuracy above performance, cost savings, or developer convenience.

**Implications:**
- The system must surface confidence scores and supporting evidence for every code suggestion
- When confidence is low, the system must explicitly flag uncertainty rather than silently guessing
- False positives (suggesting an incorrect code) are more dangerous than false negatives (missing a code) in many clinical contexts; the system must be calibrated accordingly
- All code assignment logic must be testable against known correct coding scenarios
- Changes to the RAG pipeline or LLM prompts require validation against a curated test suite of clinical notes with known correct codes

---

## 2. Data Sovereignty

All coding results must come from ingested ICD-10-CM data only. The system must never use LLM training data for code assignment. The LLM is a reasoning engine that operates on retrieved context, not a knowledge source.

**Implications:**
- The vector database (Qdrant) is the single source of truth for all ICD-10-CM codes, descriptions, guidelines, includes/excludes notes, and instructional notes
- The LLM prompt must contain explicit negative instructions forbidding the use of training knowledge for code selection
- If the retrieved context is insufficient to assign a code, the system must respond with "insufficient evidence" rather than allowing the LLM to fill gaps from training data
- Every code in a response must be traceable to a specific entry in the ingested dataset
- The ingestion pipeline must be version-aware: it must track which ICD-10-CM release was ingested and when
- Data updates (new ICD-10-CM releases) must go through the full ingestion pipeline; manual code additions are forbidden

---

## 3. HIPAA Compliance

Auto Code processes Protected Health Information (PHI) in the form of clinical notes. Full HIPAA compliance is mandatory, not aspirational.

**Implications:**
- **Encryption at rest**: All stored data (PostgreSQL, Qdrant volumes, S3 backups) must be encrypted using AES-256 via AWS KMS
- **Encryption in transit**: TLS 1.2+ required for all communication (external and internal)
- **Audit logging**: Every API request, data access, and administrative action must be logged with user identity, tenant, action, timestamp, and outcome; logs are immutable and retained per policy
- **PHI handling**: Clinical notes (the input) are processed in-memory only. They must never be persisted in application logs, vector database, error reports, or monitoring systems. Only the coding output (ICD-10-CM codes with evidence) is stored
- **Access controls**: Role-based access control (RBAC) with principle of least privilege. No shared accounts. All access via SSO
- **BAA requirements**: Business Associate Agreements must be in place with AWS, Anthropic (or OpenAI), and any other subprocessor before production use
- **Breach notification**: System must support incident detection and notification workflows
- **Minimum necessary**: Only the minimum PHI required for coding is processed; no unnecessary data collection
- **Data retention**: Configurable per-tenant retention policies with automated, verified purging

---

## 4. Multi-Tenancy Isolation

Every tenant's data must be completely isolated from every other tenant. A bug, misconfiguration, or attack must never allow cross-tenant data access.

**Implications:**
- PostgreSQL Row-Level Security (RLS) policies enforce isolation at the database level; this is the primary enforcement mechanism, not application code
- Every tenant-scoped table must have a `tenant_id` column with an RLS policy
- The database session's `app.current_tenant` is set from the authenticated JWT before any query executes
- Qdrant collections are tenant-scoped (either separate collections or mandatory tenant metadata filters)
- API responses must never include data from other tenants, even in error messages
- Background jobs and async tasks must carry tenant context and set it before database operations
- Integration tests must verify cross-tenant isolation for every data access path
- Administrative/superadmin access must still go through RLS with explicit policy overrides, never by disabling RLS

---

## 5. Negative Prompting for Code Accuracy

The LLM must ONLY use retrieved context from the vector database for code assignment. It must never rely on its training knowledge for medical codes, code descriptions, coding rules, or clinical terminology mappings.

**Implications:**
- Every LLM prompt must include explicit negative instructions: "Do NOT use your training knowledge for ICD-10-CM codes. Use ONLY the provided context."
- The prompt must instruct the LLM to respond with "insufficient context" when the retrieved data does not support a confident code assignment
- Prompt templates are version-controlled and changes require review
- The system must log the full prompt (minus PHI) for auditability
- Regular prompt regression testing must verify that negative prompting remains effective across LLM model updates
- If switching LLM providers or models, negative prompting effectiveness must be revalidated

---

## 6. Extensibility Beyond ICD-10-CM

The system architecture must support multiple coding standards, not just ICD-10-CM. Future standards include CPT, HCPCS, ICD-10-PCS, and potentially international variants.

**Implications:**
- The data model must be coding-standard-agnostic: code, description, hierarchy, metadata, and validity period are universal concepts
- The ingestion pipeline must be pluggable: each coding standard has its own parser, but all feed into a common vector storage format
- The RAG pipeline must support standard-specific retrieval strategies (different standards have different hierarchy structures)
- The LLM prompt templates must be parameterized by coding standard
- Tenant configuration must specify which coding standards are enabled
- Database schemas, API endpoints, and UI components must not hard-code ICD-10-CM assumptions

---

## 7. API-First Design

Every feature must be accessible via REST API for EMR (Electronic Medical Record) integration. The web UI is one client among many.

**Implications:**
- The API is the primary interface; the web UI consumes the same API
- OpenAPI specification is auto-generated and always current
- API versioning (URL-based: `/v1/`, `/v2/`) with a documented deprecation policy
- All API responses follow a consistent envelope format with proper HTTP status codes
- Webhooks for async operations (e.g., batch coding completion)
- Rate limiting is per-tenant and per-API-key
- API keys are supported alongside SSO for service-to-service (EMR) integration
- SDKs may be generated from the OpenAPI spec but the API is the contract

---

## 8. Evidence-Based Output

Every code assignment must cite its source from the coding standard. An unsupported code is an incorrect code.

**Implications:**
- Every code in a response includes: the code itself, its description, the source entry from the coding standard, the relevant includes/excludes notes, any applicable guidelines, and a confidence score
- The source citation must reference specific sections of the ingested ICD-10-CM data (tabular list entry, index entry, guideline section)
- Users can drill into the evidence for any suggested code to verify it
- The system must surface conflicting evidence (e.g., an excludes note that contradicts a code assignment) rather than silently resolving it
- Batch operations maintain the same evidence requirements as single-note operations

---

## 9. Auditability

Every action must be logged. Every coding decision must be traceable. The system must support compliance audits and clinical coding audits.

**Implications:**
- Immutable audit logs capture: who, what, when, where (tenant), why (the input that triggered the action), and the outcome
- Coding decisions include a full trace: input note (reference only, not stored in log), retrieved context, reranking scores, final LLM prompt (minus PHI), LLM response, and assigned codes
- Audit logs are stored separately from application data and have independent retention policies
- Audit log access requires elevated permissions and is itself audited
- The system must support export of audit data for external compliance tools
- Deletion of audit records is prohibited during the retention period

---

## 10. SaaS Architecture

Auto Code is a multi-tenant SaaS product. The architecture must support horizontal scaling, tenant isolation, and operational efficiency at scale.

**Implications:**
- Stateless application tier: no server-side sessions, no local file storage for user data
- Database connection pooling and tenant-aware query optimization
- Background job processing with tenant context and priority queuing
- Health checks, readiness probes, and graceful shutdown
- Zero-downtime deployments
- Per-tenant configuration (enabled features, rate limits, LLM provider, retention policies)
- Usage metering and billing integration points
- Tenant onboarding and offboarding automation

---

## 11. Documentation-Driven Development

Specifications before code. Decisions recorded as Architecture Decision Records (ADRs). The documentation structure is a first-class deliverable.

**Implications:**
- Before implementing a feature, the relevant spec must exist in `.specs/` or `planning/`
- Significant technical decisions require an ADR in `decisions/` documenting context, options considered, decision, and consequences
- API changes require updated OpenAPI documentation
- The documentation structure (`.specs/`, `memory/`, `planning/`, `decisions/`, `docs/`, `.ai/`) must be maintained by all contributors, including AI agents
- Code reviews should verify that documentation was updated alongside code changes
- Stale documentation is a bug

---

## 12. Security by Default

Security is not a feature to be added later. Every component must be secure by default.

**Implications:**
- **Principle of least privilege**: Services, users, and API keys have only the permissions they need
- **Input validation**: All inputs validated at the API boundary via Pydantic schemas; reject invalid input early
- **SQL injection prevention**: All database access through SQLAlchemy ORM; no raw SQL without parameterization
- **XSS prevention**: React's default escaping plus Content Security Policy headers
- **CSRF protection**: SameSite cookies, CSRF tokens for state-changing operations
- **Rate limiting**: Per-tenant and per-user limits enforced at the API gateway (WAF) and application level
- **Dependency security**: Automated dependency scanning (Dependabot/Snyk); no known critical vulnerabilities in production
- **Secrets management**: All secrets in AWS Secrets Manager; never in code, config files, or environment variables in CI logs
- **Network security**: VPC isolation, security groups with minimal ingress, no public database endpoints
- **Container security**: Minimal base images, non-root execution, read-only filesystems where possible

---

## Amendment Process

These principles may only be amended through the following process:

1. Propose the amendment in an ADR in `decisions/`
2. Document the rationale for the change and its impact on existing principles
3. Obtain explicit approval from the project lead
4. Update this constitution document
5. Review all existing code and documentation for compliance with the amended principle
