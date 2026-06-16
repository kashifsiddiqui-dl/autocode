# Recent Decisions

## Summary of Key Architectural Decisions

The following 5 decisions have been made during the initial planning phase. Each should be formally documented as an ADR in `decisions/` (pending).

---

### 1. Qdrant for Vector Database

**Decision**: Use Qdrant as the vector database for storing and retrieving ICD-10-CM code embeddings.

**Rationale**: Qdrant provides native support for hybrid search (dense + sparse vectors), payload filtering (critical for filtering by chapter/section/category), and a straightforward REST/gRPC API. It runs well as a Docker container for development and can be self-hosted or use Qdrant Cloud in production. Compared to alternatives:
- **Pinecone**: Fully managed but vendor lock-in, higher cost, less control over HNSW parameters.
- **Weaviate**: Feature-rich but heavier operational footprint, more complex configuration.
- **pgvector**: Simpler stack (reuse PostgreSQL) but weaker search performance at scale and no native sparse vector support.
- **ChromaDB**: Too lightweight for production medical coding workloads.

**Status**: Accepted. Pending formal ADR.

---

### 2. Code-Centric Chunking Strategy

**Decision**: Each ICD-10-CM code becomes one chunk/document in the vector store, with its full contextual metadata (hierarchy, includes/excludes, index entries, 7th character details).

**Rationale**: Medical coding is fundamentally about finding the right code. Unlike general RAG where documents are chunked by passages, our retrieval unit IS the code. This approach:
- Makes retrieval results directly actionable (each result is a specific code).
- Avoids the "lost in the middle" problem of long document chunks.
- Allows precise payload filtering by code hierarchy.
- Simplifies post-LLM validation (each returned code has a 1:1 mapping to a vector).

The tradeoff is larger per-chunk payloads (due to inherited parent context), but this is acceptable given the dataset size (~72,000 billable codes).

**Status**: Accepted. Pending formal ADR.

---

### 3. Azure AD OIDC for Authentication

**Decision**: Use Azure Active Directory (now Entra ID) with OpenID Connect for single sign-on authentication.

**Rationale**: Target customers are healthcare organizations, most of which use Microsoft 365 and Azure AD for identity management. Using Azure AD OIDC:
- Enables SSO with existing organizational credentials (no new passwords).
- Provides MFA enforcement via the customer's Azure AD policies.
- Supplies tenant ID for multi-tenancy isolation.
- Supports RBAC via Azure AD app roles.
- Meets healthcare organization IT security requirements.

Alternatives considered:
- **Auth0**: More flexible but adds another vendor and cost. Most healthcare orgs already have Azure AD.
- **Cognito**: AWS-native but less common in enterprise healthcare IT.
- **Custom auth**: Too risky for a HIPAA-regulated application. Proven identity providers are essential.

**Status**: Accepted. Pending formal ADR.

---

### 4. AWS for Cloud Infrastructure

**Decision**: Deploy on Amazon Web Services using a Terraform-managed infrastructure stack.

**Rationale**: AWS offers the broadest set of HIPAA-eligible services, a well-documented shared responsibility model, and the ability to sign a BAA. Specific services selected:
- **ECS Fargate**: Serverless container hosting, no EC2 instance management.
- **RDS PostgreSQL**: Managed database with automated backups, encryption, Multi-AZ.
- **S3**: Export file storage with encryption and lifecycle policies.
- **ALB + WAF**: Load balancing with web application firewall.
- **KMS**: Customer-managed encryption keys.
- **CloudWatch**: Centralized logging and monitoring.
- **Secrets Manager**: Secure credential storage with rotation.

Alternatives considered:
- **Azure**: Natural fit with Azure AD, but team has deeper AWS expertise.
- **GCP**: Strong ML/AI services but smaller HIPAA-eligible service portfolio.
- **Self-hosted**: Too much operational overhead for a SaaS startup.

**Status**: Accepted. Pending formal ADR.

---

### 5. HIPAA Compliance from Day One

**Decision**: Build HIPAA compliance into the architecture from the start, not as a retrofit.

**Rationale**: Auto Code processes clinical text that may contain PHI (Protected Health Information). Retrofitting HIPAA compliance is significantly more expensive and risky than building it in from the start. Day-one compliance means:
- Encryption at rest and in transit from the first deployment.
- Audit logging from the first API endpoint.
- RLS-based multi-tenancy from the first database table.
- PHI-aware logging (exclusion) from the first log statement.
- BAAs with all subprocessors before sending them any data.
- Security-first code review practices from the first PR.

The cost of compliance upfront is incremental. The cost of retrofitting is a rewrite.

**Status**: Accepted. Pending formal ADR.

---

## Decision Log

| # | Decision | Date | Status |
|---|----------|------|--------|
| 1 | Qdrant for vector database | 2026-06-16 | Accepted |
| 2 | Code-centric chunking strategy | 2026-06-16 | Accepted |
| 3 | Azure AD OIDC for authentication | 2026-06-16 | Accepted |
| 4 | AWS for cloud infrastructure | 2026-06-16 | Accepted |
| 5 | HIPAA compliance from day one | 2026-06-16 | Accepted |
