# Auto Code - System Architecture Overview

## 1. System Overview

Auto Code is a multi-tenant SaaS platform that automates medical coding (ICD-10-CM) using Retrieval-Augmented Generation (RAG) combined with Large Language Models. The system ingests official CMS ICD-10-CM classification data (tabular lists, alphabetic indexes, drug tables, neoplasm tables, and coding guidelines), builds a searchable vector knowledge base, and uses hybrid retrieval with LLM reasoning to suggest accurate diagnosis codes from clinical documentation.

### Core Design Principles

- **Accuracy over speed**: Multi-stage retrieval with cross-encoder reranking and post-LLM validation ensures coding precision.
- **Negative prompting**: The LLM is explicitly instructed on what NOT to code, reducing hallucinated or over-specific code assignments.
- **HIPAA compliance by design**: PHI is never stored in vector databases, LLM API calls have zero data retention, and all access is audited.
- **Multi-tenancy isolation**: PostgreSQL Row-Level Security (RLS) enforces tenant boundaries at the database level.
- **Code-set versioning**: The data pipeline supports multiple ICD-10-CM release years (e.g., April 1, 2026) side by side.

---

## 2. High-Level Component Diagram

```
                                 +---------------------------+
                                 |      End Users            |
                                 |  (Medical Coders, HIM)    |
                                 +------------+--------------+
                                              |
                                          HTTPS/TLS 1.2+
                                              |
                              +---------------v--------------+
                              |         AWS ALB / WAF        |
                              |   (SSL termination, DDoS)    |
                              +---------------+--------------+
                                              |
                              +---------------v--------------+
                              |      API Gateway (nginx)     |
                              |  rate limiting, routing,     |
                              |  static asset serving        |
                              +------+---------------+------+
                                     |               |
                        +------------v---+   +-------v-----------+
                        |   Frontend     |   |   Backend API     |
                        |   (Next.js)    |   |   (FastAPI)       |
                        |   SSR + SPA    |   |   Python 3.12+    |
                        +----------------+   +---+----+----+-----+
                                                 |    |    |
                         +-----------------------+    |    +-------------------+
                         |                            |                        |
              +----------v----------+   +-------------v-----------+   +--------v--------+
              |   PostgreSQL 16     |   |      Qdrant 1.9+        |   |  LLM APIs       |
              |   (AWS RDS)         |   |   (Vector Database)     |   |  - Claude 4     |
              |                     |   |                         |   |  - GPT-4o       |
              |  - User/tenant data |   |  - ~130K code chunks    |   |  - text-embed-  |
              |  - Audit logs       |   |  - Named vectors        |   |    3-large      |
              |  - Code metadata    |   |  - Sparse vectors       |   |  - PubMedBERT   |
              |  - Session state    |   |  - Payload filters      |   +-----------------+
              |  - RLS policies     |   +-------------------------+
              +---------------------+

                    +-------------------------------------------+
                    |           Supporting Services             |
                    |                                           |
                    |  AWS S3       - Export file storage        |
                    |  AWS KMS      - Encryption key management |
                    |  CloudWatch   - Logging & monitoring      |
                    |  Azure AD     - Identity provider (OIDC)  |
                    +-------------------------------------------+
```

---

## 3. Component Details

### 3.1 Frontend (Next.js)

| Aspect | Detail |
|---|---|
| Framework | Next.js 14+ with App Router |
| Rendering | Server-Side Rendering (SSR) for initial load, client-side SPA navigation |
| UI Library | React 18, Tailwind CSS, shadcn/ui components |
| State Management | React Query (TanStack Query) for server state, Zustand for client state |
| Authentication | MSAL.js (Microsoft Authentication Library) for Azure AD OIDC |
| Key Pages | Dashboard, Coding Workspace, Code Search, Audit Trail, Export Center, Admin Settings |

### 3.2 API Gateway (nginx)

- Reverse proxy routing `/api/*` to FastAPI backend, all other routes to Next.js
- Rate limiting: 100 requests/minute per user for coding endpoints, 1000/min for search
- Request size limits: 1MB for clinical text submissions
- CORS configuration restricted to known frontend origins
- Health check endpoint for ALB target group

### 3.3 Backend API (FastAPI)

| Aspect | Detail |
|---|---|
| Framework | FastAPI 0.110+ on Python 3.12 |
| ASGI Server | Uvicorn with Gunicorn process manager |
| Authentication | Custom middleware validating Azure AD JWT tokens |
| Authorization | RBAC decorator checking user roles from JWT claims |
| Database ORM | SQLAlchemy 2.0 with async session support |
| Vector Client | qdrant-client (Python) with async gRPC transport |
| LLM Integration | Anthropic SDK (Claude), OpenAI SDK (GPT-4o, embeddings) |
| Validation | Pydantic v2 models for all request/response schemas |
| Background Tasks | Celery with Redis broker for data ingestion and export generation |

### 3.4 PostgreSQL (AWS RDS)

Primary relational store for all structured data:

- **Tenant management**: Organizations, subscription tiers, feature flags
- **User management**: Users, roles, permissions (synced from Azure AD)
- **Code metadata**: ICD-10-CM code hierarchy, descriptions, category relationships, inclusion/exclusion notes
- **Coding sessions**: User coding requests, LLM responses, selected codes, clinical notes references
- **Audit logs**: Immutable append-only audit trail for all PHI access and coding actions
- **Export records**: Export job metadata, file references, download tracking

Row-Level Security (RLS) policies enforce tenant isolation on every table containing tenant-scoped data.

### 3.5 Qdrant (Vector Database)

Stores embedded ICD-10-CM knowledge chunks for semantic retrieval:

- **Collection**: `icd10cm_codes` with ~130,000 chunks across 4 chunk types
- **Named vectors**: `description` (text-embedding-3-large, 3072d) and `clinical` (PubMedBERT, 768d)
- **Sparse vectors**: BM25-based sparse vectors for keyword matching (hybrid search)
- **Payload fields**: `code`, `chunk_type`, `category`, `chapter`, `version_year`, `hierarchy_level`, `parent_code`
- **Payload indexes**: Indexed on `chunk_type`, `category`, `chapter`, `version_year` for filtered search

### 3.6 LLM APIs

| Model | Provider | Purpose |
|---|---|---|
| Claude Opus / Sonnet | Anthropic | Primary reasoning model for code assignment from retrieved context |
| GPT-4o | OpenAI | Fallback reasoning model |
| text-embedding-3-large | OpenAI | Description embeddings (3072 dimensions) |
| PubMedBERT | Self-hosted / HuggingFace | Clinical context embeddings (768 dimensions) |
| Cross-encoder (ms-marco-MiniLM) | Self-hosted | Reranking retrieved chunks by relevance |

All LLM API calls are configured with **zero data retention** agreements. No PHI is stored by any LLM provider.

---

## 4. Data Flow: Coding Request

This is the primary user-facing flow. A medical coder submits clinical documentation and receives ICD-10-CM code suggestions.

```
  +---------------------+
  |  User submits       |
  |  clinical text      |
  |  via Coding         |
  |  Workspace          |
  +---------+-----------+
            |
            v
  +---------+-----------+
  | Frontend sends POST |
  | /api/v1/code        |
  | { clinical_text,    |
  |   encounter_type,   |
  |   patient_context } |
  +---------+-----------+
            |
            v
  +---------+-----------+
  | API Gateway:        |
  | - Rate limit check  |
  | - Forward to backend|
  +---------+-----------+
            |
            v
  +---------+-----------+
  | FastAPI endpoint:   |
  | - JWT validation    |
  | - Tenant extraction |
  | - Input sanitization|
  | - Pydantic validation|
  +---------+-----------+
            |
            v
  +---------+----------------------------------+
  | RAG Pipeline (4-stage retrieval)            |
  |                                             |
  | Stage 1: Hybrid Search (Qdrant)             |
  |   - Embed clinical text (description vec)   |
  |   - Embed clinical text (clinical vec)       |
  |   - BM25 sparse vector query                |
  |   - Dense + sparse fusion (RRF)             |
  |   - Return top-100 candidate chunks         |
  |                                             |
  | Stage 2: Metadata Filtering                 |
  |   - Filter by version_year (active release) |
  |   - Filter by encounter_type if applicable  |
  |   - Filter by category hints from NER       |
  |   - Reduce to top-60 chunks                 |
  |                                             |
  | Stage 3: Cross-Encoder Reranking            |
  |   - Score each chunk against clinical text   |
  |   - ms-marco-MiniLM cross-encoder           |
  |   - Rerank and take top-20 chunks           |
  |                                             |
  | Stage 4: Hierarchy Expansion (PostgreSQL)   |
  |   - For each candidate code, fetch parent   |
  |     category and chapter context            |
  |   - Fetch inclusion/exclusion notes         |
  |   - Fetch "code first" / "use additional    |
  |     code" instructions                      |
  |   - Attach coding guidelines snippets       |
  |   - Produce final context package           |
  +---------------------+-----------------------+
                        |
                        v
  +---------------------+-----------------------+
  | LLM Reasoning with Negative Prompting       |
  |                                             |
  | System prompt includes:                     |
  | - Role: expert medical coder                |
  | - Retrieved context (top-20 chunks +        |
  |   hierarchy data)                           |
  | - NEGATIVE instructions:                    |
  |   "Do NOT assign codes that..."             |
  |   - Are more specific than documented       |
  |   - Require clinical detail not present     |
  |   - Are excluded by Excludes1/Excludes2     |
  | - Output format: structured JSON            |
  |                                             |
  | Response: ranked code suggestions with      |
  |   confidence scores and reasoning           |
  +---------------------+-----------------------+
                        |
                        v
  +---------------------+-----------------------+
  | Post-LLM Validation                        |
  |                                             |
  | - Verify all suggested codes exist in       |
  |   ICD-10-CM master table                    |
  | - Check code validity (billable vs header)  |
  | - Validate Excludes1/Excludes2 conflicts   |
  |   between suggested codes                  |
  | - Verify code specificity requirements      |
  |   (7th character, laterality)              |
  | - Flag codes that need additional codes     |
  | - Attach confidence calibration             |
  +---------------------+-----------------------+
                        |
                        v
  +---------------------+-----------------------+
  | Response Assembly                           |
  |                                             |
  | - Primary code suggestions (ranked)         |
  | - Supporting evidence snippets              |
  | - Coding notes and warnings                 |
  | - Confidence scores (high/medium/low)       |
  | - "Requires review" flags                   |
  +---------------------+-----------------------+
                        |
                        v
  +---------------------+-----------------------+
  | Audit Logging                               |
  |                                             |
  | - Log request: user, tenant, timestamp,     |
  |   input hash (not raw PHI), IP, user agent  |
  | - Log response: codes suggested, codes      |
  |   accepted, model used, latency             |
  +---------------------+-----------------------+
                        |
                        v
  +---------------------+-----------------------+
  | Return JSON response to frontend            |
  | HTTP 200 with coding suggestions            |
  +---------------------------------------------+
```

---

## 5. Multi-Tenancy Architecture

### Strategy: Shared Database, Shared Schema, Row-Level Security

All tenants share a single PostgreSQL database and schema. Tenant isolation is enforced at three layers:

```
  +-----------------------------------------------------------+
  |                    Application Layer                       |
  |                                                           |
  |  JWT token contains tenant_id claim                       |
  |  FastAPI middleware extracts tenant_id                     |
  |  SQLAlchemy session sets: SET app.current_tenant = 'X'    |
  +-----------------------------------------------------------+
                              |
  +-----------------------------------------------------------+
  |                    Database Layer                          |
  |                                                           |
  |  Every tenant-scoped table has tenant_id column           |
  |  RLS policy: WHERE tenant_id = current_setting(           |
  |    'app.current_tenant')                                  |
  |  Even if application code omits WHERE clause, RLS         |
  |  prevents cross-tenant data access                        |
  +-----------------------------------------------------------+
                              |
  +-----------------------------------------------------------+
  |                    Vector Store Layer                      |
  |                                                           |
  |  ICD-10-CM knowledge base is shared (not tenant-specific) |
  |  Coding results are stored in PostgreSQL (tenant-scoped)  |
  |  No PHI in Qdrant - only ICD-10-CM reference data         |
  +-----------------------------------------------------------+
```

### Tenant-Scoped Tables

All of the following tables include a `tenant_id UUID NOT NULL` column with RLS policies:

- `users` - User accounts within a tenant
- `coding_sessions` - Coding request/response history
- `coding_results` - Accepted/rejected code assignments
- `audit_logs` - Tenant-specific audit trail
- `exports` - Export job records
- `settings` - Tenant-specific configuration (preferred code version, LLM model, etc.)

### Shared Tables (No RLS)

- `icd10cm_codes` - Master code table (read-only reference data)
- `icd10cm_categories` - Category hierarchy
- `icd10cm_guidelines` - Coding guidelines
- `tenants` - Tenant registry (admin-only access)
- `subscription_plans` - Plan definitions

### RLS Policy Example

```sql
ALTER TABLE coding_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON coding_sessions
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_insert ON coding_sessions
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid);
```

---

## 6. Authentication Flow

```
  +----------+       +----------+       +----------+       +----------+
  |  Browser |       |  Azure   |       | FastAPI  |       | Postgres |
  |          |       |  AD      |       | Backend  |       |          |
  +----+-----+       +----+-----+       +----+-----+       +----+-----+
       |                   |                  |                  |
       | 1. Click "Sign In"|                  |                  |
       |------------------>|                  |                  |
       |                   |                  |                  |
       | 2. Azure AD login |                  |                  |
       |   page (OIDC)     |                  |                  |
       |<------------------|                  |                  |
       |                   |                  |                  |
       | 3. User enters    |                  |                  |
       |   credentials +   |                  |                  |
       |   MFA              |                  |                  |
       |------------------>|                  |                  |
       |                   |                  |                  |
       | 4. Authorization  |                  |                  |
       |   code redirect   |                  |                  |
       |<------------------|                  |                  |
       |                   |                  |                  |
       | 5. POST /api/v1/auth/callback        |                  |
       |   with auth code  |                  |                  |
       |---------------------------------------->|                  |
       |                   |                  |                  |
       |                   | 6. Exchange code |                  |
       |                   |   for tokens     |                  |
       |                   |<-----------------|                  |
       |                   |                  |                  |
       |                   | 7. ID token +   |                  |
       |                   |   access token   |                  |
       |                   |----------------->|                  |
       |                   |                  |                  |
       |                   |                  | 8. Validate ID   |
       |                   |                  |   token, extract |
       |                   |                  |   user info,     |
       |                   |                  |   tenant_id      |
       |                   |                  |                  |
       |                   |                  | 9. Upsert user   |
       |                   |                  |----------------->|
       |                   |                  |                  |
       |                   |                  | 10. Issue app JWT|
       |                   |                  |   access (15min) |
       |                   |                  |   refresh (7d)   |
       |                   |                  |                  |
       | 11. Set httpOnly  |                  |                  |
       |   secure cookies  |                  |                  |
       |<----------------------------------------|                  |
       |                   |                  |                  |
       | 12. Subsequent    |                  |                  |
       |   API requests    |                  |                  |
       |   include JWT     |                  |                  |
       |   cookie           |                  |                  |
       |---------------------------------------->|                  |
       |                   |                  |                  |
       |                   |                  | 13. Middleware:  |
       |                   |                  |   validate JWT,  |
       |                   |                  |   extract        |
       |                   |                  |   tenant_id,     |
       |                   |                  |   SET RLS context|
       |                   |                  |----------------->|
```

### JWT Token Structure

```json
{
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "email": "coder@hospital.org",
  "roles": ["coder"],
  "permissions": ["code:read", "code:write", "export:read"],
  "iat": 1718500000,
  "exp": 1718500900,
  "iss": "autocode-api"
}
```

### Token Configuration

| Parameter | Value | Rationale |
|---|---|---|
| Access token TTL | 15 minutes | Short-lived to limit exposure from token theft |
| Refresh token TTL | 7 days | Balances UX (no re-login) with security |
| Refresh rotation | Enabled | Each refresh issues a new refresh token, old one is revoked |
| Cookie flags | `httpOnly`, `Secure`, `SameSite=Strict` | Prevents XSS token theft and CSRF |
| Token signing | RS256 (asymmetric) | Backend validates without sharing secret |

---

## 7. RAG Pipeline Architecture

See [rag-pipeline.md](./rag-pipeline.md) for the deep dive. Summary below.

### Four-Stage Retrieval

1. **Hybrid Search**: Dense vectors (text-embedding-3-large + PubMedBERT named vectors) combined with BM25 sparse vectors using Reciprocal Rank Fusion (RRF). Returns top-100 candidates.
2. **Metadata Filtering**: Filter by ICD-10-CM version year, chunk type relevance, and optional category hints from lightweight NER. Reduces to top-60.
3. **Cross-Encoder Reranking**: ms-marco-MiniLM-L-12 scores each (query, chunk) pair. Reranks to top-20.
4. **Hierarchy Expansion**: For each candidate code, fetch parent categories, inclusion/exclusion notes, and coding instructions from PostgreSQL. Produces the final context package.

### Negative Prompting Strategy

The LLM system prompt explicitly instructs the model on common coding errors to avoid:

- Do not assign codes more specific than what the clinical documentation supports
- Do not ignore Excludes1 (mutually exclusive) and Excludes2 (not included here) notes
- Do not assign header/category codes when a more specific billable code is required
- Do not assume laterality, episode of care, or sequela unless documented

---

## 8. Data Ingestion Pipeline

```
  +-------------------+     +------------------+     +------------------+
  |  CMS ICD-10-CM    |     |  XML Parsers     |     |  Chunking Engine |
  |  Source Files     |---->|                  |---->|                  |
  |                   |     |  - Tabular XML   |     |  4 chunk types:  |
  |  - Tabular XML    |     |  - Index XML     |     |  - Code context  |
  |  - Index XML      |     |  - Drug XML      |     |  - Index entry   |
  |  - Drug XML       |     |  - Neoplasm XML  |     |  - Drug table    |
  |  - Neoplasm XML   |     |  - Guidelines PDF|     |  - Neoplasm tbl  |
  |  - Guidelines PDF |     +------------------+     +--------+---------+
  |  - Addenda        |                                       |
  +-------------------+                                       v
                                                  +-----------+---------+
                                                  |  Embedding Service  |
                                                  |                     |
                                                  |  - text-embedding-  |
                                                  |    3-large (desc)   |
                                                  |  - PubMedBERT       |
                                                  |    (clinical)       |
                                                  |  - BM25 sparse      |
                                                  +----+----------+-----+
                                                       |          |
                                              +--------v---+  +---v----------+
                                              |  Qdrant    |  | PostgreSQL   |
                                              |            |  |              |
                                              | Vectors +  |  | Code master  |
                                              | payloads   |  | table,       |
                                              |            |  | hierarchy,   |
                                              +------------+  | guidelines   |
                                                              +--------------+
```

### Ingestion Steps

1. **Download**: Fetch latest ICD-10-CM release from CMS (XML + PDF formats)
2. **Parse XML**: Extract structured code data from tabular, index, drug, and neoplasm XML files using `lxml`
3. **Parse Guidelines**: Extract coding guidelines from PDF using structured extraction
4. **Build Hierarchy**: Construct chapter > section > category > subcategory > code tree in PostgreSQL
5. **Generate Chunks**: Create ~130K chunks across 4 types with code-centric boundaries
6. **Embed**: Generate dual named vectors (description + clinical) and sparse BM25 vectors for each chunk
7. **Load Qdrant**: Upsert vectors with payload metadata into `icd10cm_codes` collection
8. **Load PostgreSQL**: Insert/update code metadata, hierarchy, and guideline records
9. **Validate**: Run integrity checks comparing chunk count to expected code count, verify searchability
10. **Version Tag**: Mark the release version as active, previous version as archived

---

## 9. Export System

The export system generates downloadable files from coding session results.

### Supported Formats

| Format | Use Case | Generation |
|---|---|---|
| PDF | Formal coding reports, compliance documentation | WeasyPrint with HTML templates |
| CSV | Bulk data export for billing systems | Python csv module, streaming |
| JSON | API integration with EHR/billing systems | Direct serialization |
| HL7 FHIR | Standards-based interoperability | FHIR R4 DiagnosticReport resource |

### Export Flow

1. User requests export from Coding Workspace or Audit Trail
2. FastAPI creates an export job record in PostgreSQL (status: `pending`)
3. Celery worker picks up the job asynchronously
4. Worker queries coding results (tenant-scoped via RLS)
5. Worker generates the file in the requested format
6. File is encrypted and uploaded to S3 (SSE-KMS)
7. Job status updated to `completed` with a pre-signed download URL (15-minute expiry)
8. User is notified (WebSocket or polling) and can download
9. Audit log records the export event

---

## 10. Infrastructure (AWS)

```
  +---------------------------------------------------------------+
  |                        AWS Account                            |
  |                                                               |
  |  +---------------------------+  +---------------------------+ |
  |  |        Public Subnet      |  |       Public Subnet       | |
  |  |        (us-east-1a)       |  |       (us-east-1b)        | |
  |  |                           |  |                           | |
  |  |  +---------------------+  |  |  +---------------------+  | |
  |  |  |   ALB               |  |  |  |   ALB               |  | |
  |  |  |   (internet-facing) |  |  |  |   (target group)    |  | |
  |  |  +---------------------+  |  |  +---------------------+  | |
  |  +---------------------------+  +---------------------------+ |
  |                                                               |
  |  +---------------------------+  +---------------------------+ |
  |  |       Private Subnet      |  |      Private Subnet       | |
  |  |       (us-east-1a)        |  |      (us-east-1b)         | |
  |  |                           |  |                           | |
  |  |  +---------------------+  |  |  +---------------------+  | |
  |  |  |  EC2: App Server    |  |  |  |  EC2: App Server    |  | |
  |  |  |  nginx + FastAPI    |  |  |  |  nginx + FastAPI    |  | |
  |  |  |  + Next.js          |  |  |  |  + Next.js          |  | |
  |  |  +---------------------+  |  |  +---------------------+  | |
  |  |                           |  |                           | |
  |  |  +---------------------+  |  |  +---------------------+  | |
  |  |  |  EC2: Qdrant        |  |  |  |  EC2: Celery Worker |  | |
  |  |  |  (vector DB)        |  |  |  |  + Redis            |  | |
  |  |  +---------------------+  |  |  +---------------------+  | |
  |  +---------------------------+  +---------------------------+ |
  |                                                               |
  |  +---------------------------+  +---------------------------+ |
  |  |      Data Subnet          |  |     Data Subnet           | |
  |  |      (us-east-1a)         |  |     (us-east-1b)          | |
  |  |                           |  |                           | |
  |  |  +---------------------+  |  |  +---------------------+  | |
  |  |  |  RDS PostgreSQL 16  |  |  |  |  RDS PostgreSQL 16  |  | |
  |  |  |  (Primary)          |  |  |  |  (Standby)          |  | |
  |  |  |  Multi-AZ           |  |  |  |  Multi-AZ           |  | |
  |  |  +---------------------+  |  |  +---------------------+  | |
  |  +---------------------------+  +---------------------------+ |
  |                                                               |
  |  +----------------------------------------------------------+ |
  |  |  Shared Services                                         | |
  |  |  S3: exports, backups     KMS: encryption keys           | |
  |  |  CloudWatch: logs/metrics WAF: web app firewall          | |
  |  |  Secrets Manager: API keys, DB credentials               | |
  |  +----------------------------------------------------------+ |
  +---------------------------------------------------------------+
```

### AWS Service Configuration

| Service | Configuration | Purpose |
|---|---|---|
| EC2 (App) | c6i.xlarge (4 vCPU, 8GB), Auto Scaling Group (2-8 instances) | Application servers |
| EC2 (Qdrant) | r6i.xlarge (4 vCPU, 32GB), dedicated | Vector database (memory-optimized) |
| RDS PostgreSQL | db.r6g.large, Multi-AZ, encrypted, automated backups | Primary datastore |
| ALB | Internet-facing, HTTPS only, WAF integration | Load balancing |
| S3 | SSE-KMS encryption, versioning, lifecycle rules | Export storage |
| KMS | CMK for RDS, S3, EBS encryption | Key management |
| WAF | OWASP Core Rule Set, rate limiting, geo-blocking | Web security |
| CloudWatch | Log groups, custom metrics, alarms, dashboards | Observability |
| Secrets Manager | Rotation enabled for DB credentials | Secret management |

---

## 11. Scalability Considerations

### Current Scale Targets

- **Users**: Up to 500 concurrent users across all tenants
- **Coding requests**: ~50 requests/second sustained, 200/second burst
- **Vector search**: <100ms p95 latency for hybrid search
- **End-to-end coding**: <5 seconds p95 for full pipeline (search + LLM + validation)
- **Data volume**: ~130K chunks in Qdrant, ~100K codes in PostgreSQL

### Horizontal Scaling

- **Application tier**: Auto Scaling Group behind ALB, stateless FastAPI servers
- **Database reads**: PostgreSQL read replicas for analytics and reporting queries
- **Background jobs**: Multiple Celery workers, scale independently from API servers
- **Qdrant**: Sharded collections if vector count exceeds single-node capacity

### Vertical Scaling

- **Qdrant node**: Scale to r6i.2xlarge or 4xlarge for larger collections (future ICD-10-PCS, CPT)
- **RDS**: Scale instance class for higher connection counts

### Caching Strategy

- **Redis**: Cache frequently accessed code metadata, user sessions, rate limit counters
- **Application-level**: Cache embedding results for common clinical phrases (LRU, 1-hour TTL)
- **CDN**: CloudFront for static Next.js assets

### Future Scaling Paths

- **Qdrant Cloud**: Migrate to managed Qdrant for automatic scaling and replication
- **ECS/EKS**: Containerize application for finer-grained scaling
- **Multi-region**: Deploy in us-west-2 for disaster recovery and lower latency for West Coast users
- **Code set expansion**: Architecture supports adding ICD-10-PCS, CPT, HCPCS as additional Qdrant collections
