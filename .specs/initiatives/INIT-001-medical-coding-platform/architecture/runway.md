# Architecture Runway: Foundation Work

## Initiative: INIT-001 Medical Coding Platform
## Last Updated: 2026-06-16

---

## Overview

This document defines the foundational infrastructure and architecture work required before feature development can begin. All items here are prerequisites for Release 1 features.

---

## 1. Directory Structure

```
autocode/
├── .specs/                          # Specifications & planning
│   ├── initiatives/
│   ├── features/
│   ├── templates/
│   ├── workflows/
│   └── registry/
├── data/
│   ├── ICD-10-CM/                   # Raw ICD-10-CM source files (gitignored)
│   └── schemas/                     # Coding standard manifests
├── src/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   ├── v1/
│   │   │   │   │   ├── endpoints/   # Route handlers
│   │   │   │   │   └── schemas/     # Pydantic request/response models
│   │   │   │   └── deps.py          # Dependency injection
│   │   │   ├── core/
│   │   │   │   ├── config.py        # Settings & environment config
│   │   │   │   ├── security.py      # Auth, JWT, RBAC
│   │   │   │   └── logging.py       # Structured logging
│   │   │   ├── db/
│   │   │   │   ├── models/          # SQLAlchemy models
│   │   │   │   ├── migrations/      # Alembic migrations
│   │   │   │   └── session.py       # Database session management
│   │   │   ├── services/
│   │   │   │   ├── ingestion/       # Data ingestion pipeline
│   │   │   │   ├── rag/             # RAG retrieval & reranking
│   │   │   │   ├── coding/          # Coding analysis orchestration
│   │   │   │   └── export/          # Export generation
│   │   │   └── main.py              # FastAPI application entry
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   ├── integration/
│   │   │   └── conftest.py
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   └── frontend/
│       ├── src/
│       │   ├── app/                  # Next.js app router
│       │   ├── components/           # React components
│       │   ├── hooks/                # Custom React hooks
│       │   ├── lib/                  # Utilities & API client
│       │   └── types/                # TypeScript type definitions
│       ├── package.json
│       └── Dockerfile
├── infra/
│   ├── docker/
│   │   └── docker-compose.yml       # Local development orchestration
│   └── terraform/                   # Cloud infrastructure (future)
├── scripts/
│   ├── ingest.py                    # Data ingestion CLI
│   └── seed.py                      # Development seed data
└── docs/                            # Generated documentation
```

---

## 2. Docker Compose Setup

### Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `api` | Custom (FastAPI) | 8000 | Backend API server |
| `web` | Custom (Next.js) | 3000 | Frontend web application |
| `postgres` | postgres:16-alpine | 5432 | Primary database |
| `qdrant` | qdrant/qdrant:v1.13 | 6333, 6334 | Vector database |
| `redis` | redis:7-alpine | 6379 | Session cache & rate limiting |

### Volumes

- `pgdata` -- PostgreSQL data persistence
- `qdrant_data` -- Qdrant vector data persistence

### Networks

- `autocode-net` -- Internal bridge network for service communication

### Environment Variables

```
# PostgreSQL
POSTGRES_DB=autocode
POSTGRES_USER=autocode
POSTGRES_PASSWORD=<secret>

# Qdrant
QDRANT__SERVICE__API_KEY=<secret>

# API
DATABASE_URL=postgresql+asyncpg://autocode:<secret>@postgres:5432/autocode
QDRANT_URL=http://qdrant:6333
REDIS_URL=redis://redis:6379/0
OPENAI_API_KEY=<secret>          # For embeddings (text-embedding-3-small)
ANTHROPIC_API_KEY=<secret>       # For LLM analysis (Claude)
AZURE_AD_TENANT_ID=<tenant>
AZURE_AD_CLIENT_ID=<client>
AZURE_AD_CLIENT_SECRET=<secret>

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 3. Database Schema

### Core Tables

```sql
-- Coding standards registry
CREATE TABLE coding_standards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,           -- e.g., "ICD-10-CM"
    version VARCHAR(20) NOT NULL,         -- e.g., "2026"
    effective_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(name, version)
);

-- ICD-10-CM codes (and future standards)
CREATE TABLE codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    standard_id UUID REFERENCES coding_standards(id),
    code VARCHAR(20) NOT NULL,            -- e.g., "A01.0"
    description TEXT NOT NULL,            -- Short description
    long_description TEXT,                -- Full description
    chapter VARCHAR(10),                  -- e.g., "1"
    chapter_description TEXT,             -- e.g., "Certain infectious..."
    section VARCHAR(20),                  -- Section range
    section_description TEXT,
    category VARCHAR(10),                 -- e.g., "A01"
    is_billable BOOLEAN DEFAULT false,    -- Only leaf codes are billable
    parent_code VARCHAR(20),              -- Parent in hierarchy
    metadata JSONB,                       -- Includes, excludes, notes
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(standard_id, code)
);

-- Tenants (organizations)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    azure_tenant_id VARCHAR(255),
    default_standard_id UUID REFERENCES coding_standards(id),
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'coder',  -- admin, coder, viewer
    azure_oid VARCHAR(255),                      -- Azure AD object ID
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(tenant_id, email)
);

-- Coding sessions
CREATE TABLE coding_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),
    patient_name VARCHAR(255),
    patient_dob DATE,
    patient_mrn VARCHAR(100),
    patient_gender VARCHAR(20),
    clinical_notes TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'draft',   -- draft, in_review, completed, exported
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Coding results (per session)
CREATE TABLE coding_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES coding_sessions(id) ON DELETE CASCADE,
    code_id UUID REFERENCES codes(id),
    code VARCHAR(20) NOT NULL,
    description TEXT NOT NULL,
    confidence FLOAT NOT NULL,
    status VARCHAR(50) DEFAULT 'suggested',  -- suggested, accepted, rejected
    reasoning TEXT,                            -- LLM's explanation
    source_chunks JSONB,                      -- References to Qdrant chunks
    hierarchy JSONB,                          -- Chapter > section > category path
    excludes JSONB,                           -- Excludes1 and Excludes2 notes
    created_at TIMESTAMPTZ DEFAULT now()
);

-- API keys (for EMR integration)
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    key_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    scopes JSONB DEFAULT '["coding:read", "coding:write"]',
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Row-level security policies
ALTER TABLE coding_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE coding_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- RLS policies ensure tenant isolation
CREATE POLICY tenant_isolation_sessions ON coding_sessions
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

CREATE POLICY tenant_isolation_results ON coding_results
    USING (session_id IN (
        SELECT id FROM coding_sessions
        WHERE tenant_id = current_setting('app.current_tenant_id')::UUID
    ));

CREATE POLICY tenant_isolation_users ON users
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);
```

### Indexes

```sql
CREATE INDEX idx_codes_standard_code ON codes(standard_id, code);
CREATE INDEX idx_codes_chapter ON codes(standard_id, chapter);
CREATE INDEX idx_codes_category ON codes(standard_id, category);
CREATE INDEX idx_codes_billable ON codes(standard_id, is_billable);
CREATE INDEX idx_sessions_tenant ON coding_sessions(tenant_id);
CREATE INDEX idx_sessions_user ON coding_sessions(user_id);
CREATE INDEX idx_results_session ON coding_results(session_id);
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
```

---

## 4. Qdrant Vector Database Setup

### Collections

#### `icd10cm_chunks`

| Parameter | Value |
|-----------|-------|
| Vector size | 1536 (text-embedding-3-small) |
| Distance metric | Cosine |
| On-disk payload | true |
| Optimizers config | indexing_threshold: 20000 |

#### Payload Schema

```json
{
  "code": "string",
  "description": "string",
  "chunk_type": "string",       // tabular, index, drug, neoplasm, eindex
  "chapter": "string",
  "section": "string",
  "category": "string",
  "is_billable": "boolean",
  "hierarchy_path": "string",   // "Chapter 1 > A00-A09 > A01 > A01.0"
  "content": "string",          // The text that was embedded
  "parent_code": "string",
  "standard_id": "string",
  "standard_version": "string"
}
```

#### Payload Indexes

- `chunk_type` -- keyword index for filtering by source file type
- `chapter` -- keyword index for chapter filtering
- `is_billable` -- boolean index for billable-only queries
- `standard_id` -- keyword index for multi-standard support
- `code` -- keyword index for exact code lookup

### Estimated Collection Size

- ~98,186 codes from tabular data
- ~30,000 index entries
- ~2,000 neoplasm table entries
- ~1,500 drug/substance entries
- Total: ~130,000 chunks (approximately 200MB vector data at 1536 dimensions)

---

## 5. Ingestion Pipeline Architecture

```
XML Source Files
      |
      v
[XML Parser] -- Standard-specific parsers for each XML format
      |
      v
[Code Extractor] -- Extract structured code records
      |
      v
[PostgreSQL Loader] -- Bulk insert into codes table
      |
      v
[Chunk Generator] -- Create text chunks for embedding
      |
      v
[Embedding Generator] -- OpenAI text-embedding-3-small
      |        |
      |        v
      |   [Batch Processing] -- 2048-token chunks, batch size 100
      |
      v
[Qdrant Loader] -- Upsert vectors with payload metadata
      |
      v
[Validation] -- Count verification, sample query tests
```

### XML Source Files

| File | Content | Estimated Records |
|------|---------|-------------------|
| icd10c-tabular-April-1-2026.xml | Full code hierarchy with descriptions, includes, excludes | ~98,186 |
| icd10cm-index-April-1-2026-XML.xml | Alphabetical index of conditions | ~30,000 |
| icd10cm-drug-April-1-2026-XML.xml | Table of drugs and chemicals | ~1,500 |
| icd10cm-neoplasm-April-1-2026-XML.xml | Neoplasm table | ~2,000 |
| icd10cm-eindex-April-1-2026-XML.xml | External causes index | ~5,000 |

---

## 6. Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Backend Framework | FastAPI | 0.115+ | Async REST API with SSE |
| Python | Python | 3.12+ | Backend runtime |
| ORM | SQLAlchemy | 2.0+ | Async database access |
| Migrations | Alembic | 1.14+ | Schema migrations |
| Vector DB Client | qdrant-client | 1.13+ | Vector operations |
| Embeddings | OpenAI API | text-embedding-3-small | 1536-dim embeddings |
| LLM | Anthropic API | Claude Sonnet | Clinical text analysis |
| Cross-Encoder | sentence-transformers | ms-marco-MiniLM-L-12-v2 | Reranking |
| Frontend Framework | Next.js | 15+ | React SSR/CSR |
| UI Library | shadcn/ui + Tailwind | latest | Component library |
| State Management | Zustand | 5+ | Client state |
| Database | PostgreSQL | 16 | Primary data store |
| Vector Database | Qdrant | 1.13 | Semantic search |
| Cache | Redis | 7 | Sessions & rate limiting |
| Containerization | Docker Compose | 2.x | Local development |

---

## 7. Runway Checklist

- [ ] Directory structure created per specification
- [ ] Docker Compose file with all services configured
- [ ] PostgreSQL schema migration (initial)
- [ ] Qdrant collection created with proper configuration
- [ ] Backend project scaffolded (FastAPI + dependencies)
- [ ] Frontend project scaffolded (Next.js + dependencies)
- [ ] Environment variable templates (.env.example)
- [ ] Development seed script
- [ ] CI/CD pipeline configuration (future)
- [ ] Monitoring & logging setup (future)
