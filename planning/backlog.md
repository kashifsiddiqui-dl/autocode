# Auto Code - Feature Backlog

Priority levels:
- **P0** - Must have for MVP. Blocks launch.
- **P1** - Should have for launch. Significant value, strong user expectation.
- **P2** - Nice to have. Enhances experience but not blocking.
- **P3** - Future consideration. Deferred to post-launch.

Status: `planned` | `in-progress` | `done` | `deferred`

---

## Core Coding Assistant

| ID | Feature | Priority | Status | Phase | Notes |
|---|---|---|---|---|---|
| CA-01 | Single clinical description input with code recommendation | P0 | planned | 3 | Core product function. Textarea input, structured response. |
| CA-02 | Streaming response for real-time LLM output | P0 | planned | 3 | SSE-based streaming. Critical for UX -- reduces perceived latency. |
| CA-03 | Confidence scoring on each recommendation | P0 | planned | 3 | 0.0-1.0 scale with visual indicator (green/yellow/red). |
| CA-04 | Coding instruction warnings (Excludes1, Code First, Use Additional) | P0 | planned | 3 | Must surface these to prevent coding errors. |
| CA-05 | Hallucination detection and filtering | P0 | planned | 3 | Programmatic validation that all recommended codes exist in retrieved context. |
| CA-06 | Code detail view (full context, hierarchy, excludes) | P1 | planned | 5 | Click a code to see its complete ICD-10-CM entry with inherited context. |
| CA-07 | Copy code to clipboard | P1 | planned | 5 | One-click copy for individual codes. |
| CA-08 | Multi-code session (accumulate codes for an encounter) | P1 | planned | 5 | Add multiple codes to a "coding session" for a single patient encounter. |
| CA-09 | 7th character selector | P1 | planned | 5 | Interactive selector for laterality, encounter type when applicable. |
| CA-10 | Suggested follow-up queries | P2 | planned | 6 | After a recommendation, suggest related coding questions. |
| CA-11 | Code comparison (side-by-side two codes) | P2 | planned | 6 | Compare descriptions, excludes, context of two similar codes. |
| CA-12 | Voice input for clinical description | P3 | deferred | - | Browser speech-to-text API. Accessibility feature. |

## Search & Browse

| ID | Feature | Priority | Status | Phase | Notes |
|---|---|---|---|---|---|
| SB-01 | Code search by identifier (e.g., "E11.22") | P0 | planned | 3 | Direct code lookup returning full code details. |
| SB-02 | Description search (semantic) | P0 | planned | 3 | Natural language search across code descriptions. |
| SB-03 | Filters: chapter, billable status, code type | P1 | planned | 5 | Faceted filtering on search results. |
| SB-04 | Hierarchical code browser (chapter > section > category > code) | P2 | planned | 5 | Tree-view navigation of the ICD-10-CM hierarchy. |
| SB-05 | Drug table lookup by substance name | P2 | planned | 5 | Search the Table of Drugs and Chemicals. |
| SB-06 | Neoplasm table lookup by anatomical site | P2 | planned | 5 | Search the Neoplasm Table. |
| SB-07 | Recently viewed codes | P2 | planned | 5 | Quick access to codes the user has recently looked up. |
| SB-08 | Bookmarked/favorite codes | P3 | deferred | - | User-specific saved codes for frequent use. |

## History & Audit

| ID | Feature | Priority | Status | Phase | Notes |
|---|---|---|---|---|---|
| HA-01 | Coding session history (list of past queries + results) | P0 | planned | 5 | Required for audit trail and user reference. |
| HA-02 | Session detail view (query, retrieved chunks, LLM response) | P1 | planned | 5 | Full transparency into how a recommendation was generated. |
| HA-03 | Feedback on recommendations (thumbs up/down) | P1 | planned | 5 | Captures user satisfaction for quality monitoring. |
| HA-04 | Correction submission (user provides the correct code) | P1 | planned | 5 | Structured feedback for retrieval/prompt tuning. |
| HA-05 | Session search and filtering (by date, code, query text) | P2 | planned | 6 | Find past sessions by various criteria. |
| HA-06 | Authentication audit log viewer (admin) | P1 | planned | 5 | HIPAA requirement: who logged in when, from where. |
| HA-07 | Usage analytics dashboard (admin) | P2 | planned | 6 | Query volume, code distribution, user activity. |

## Export

| ID | Feature | Priority | Status | Phase | Notes |
|---|---|---|---|---|---|
| EX-01 | Export coding session as CSV | P1 | planned | 6 | Code, description, confidence in CSV format. |
| EX-02 | Export coding session as PDF report | P2 | planned | 6 | Formatted report with branding, suitable for records. |
| EX-03 | Export as JSON (FHIR-compatible) | P2 | planned | 6 | Structured output for system integration. |
| EX-04 | Batch coding (CSV upload of clinical descriptions) | P2 | planned | 6 | Process multiple descriptions in bulk. |
| EX-05 | Export history in bulk (date range) | P3 | deferred | - | Compliance export for audit periods. |

## Authentication & Multi-Tenancy

| ID | Feature | Priority | Status | Phase | Notes |
|---|---|---|---|---|---|
| AM-01 | Azure AD OIDC SSO login | P0 | planned | 4 | Primary authentication method. |
| AM-02 | JWT-based session management (access + refresh tokens) | P0 | planned | 4 | 15min access, 7d refresh with rotation. |
| AM-03 | Multi-tenant data isolation (RLS) | P0 | planned | 4 | Every query scoped to authenticated tenant. |
| AM-04 | Role-based access control (admin, coder, reviewer, readonly) | P0 | planned | 4 | Mapped from Azure AD groups. |
| AM-05 | User management (admin: list, invite, deactivate) | P1 | planned | 4 | Admin panel for user administration. |
| AM-06 | Tenant settings (LLM provider, model, custom prompt) | P1 | planned | 4 | Per-tenant configuration of AI behavior. |
| AM-07 | Session revocation (admin: revoke user sessions) | P1 | planned | 4 | Security control for compromised accounts. |
| AM-08 | Username/password + TOTP fallback auth | P2 | deferred | - | For small practices without Azure AD. |
| AM-09 | SAML 2.0 support | P3 | deferred | - | Legacy IdP support for specific enterprises. |
| AM-10 | Google Workspace OIDC | P3 | deferred | - | Alternative IdP support. |

## LLM & AI

| ID | Feature | Priority | Status | Phase | Notes |
|---|---|---|---|---|---|
| AI-01 | Anthropic Claude provider | P0 | planned | 3 | Primary LLM provider. |
| AI-02 | OpenAI GPT provider | P0 | planned | 3 | Secondary/fallback LLM provider. |
| AI-03 | Provider fallback on failure | P1 | planned | 3 | Auto-switch if primary provider is down. |
| AI-04 | LLM response caching (same query + same context = cached response) | P2 | planned | 6 | Reduce API costs for repeated queries. |
| AI-05 | A/B testing framework for prompts | P3 | deferred | - | Compare prompt variants on live traffic. |
| AI-06 | Fine-tuned embedding model | P3 | deferred | - | Requires production feedback data. |
| AI-07 | Self-hosted open-source LLM option | P3 | deferred | - | For customers requiring full on-premise. |

## Infrastructure & Operations

| ID | Feature | Priority | Status | Phase | Notes |
|---|---|---|---|---|---|
| IO-01 | Docker Compose local development | P0 | planned | 1 | Local dev environment with all services. |
| IO-02 | CI pipeline (lint, test, build, scan) | P0 | planned | 7 | Automated quality gates. |
| IO-03 | CD pipeline (staging + production) | P0 | planned | 7 | Automated deployment. |
| IO-04 | Terraform infrastructure provisioning | P1 | planned | 7 | Repeatable Azure infrastructure. |
| IO-05 | Monitoring dashboards | P1 | planned | 7 | API latency, error rates, Qdrant health. |
| IO-06 | Alerting (error spikes, auth failures, high latency) | P1 | planned | 7 | PagerDuty/Slack integration. |
| IO-07 | Automated database backups | P0 | planned | 7 | Daily PostgreSQL, pre/post-ingestion Qdrant. |
| IO-08 | Log aggregation | P1 | planned | 7 | Centralized structured logging. |
| IO-09 | Cost tracking (LLM API costs per tenant) | P2 | planned | 7 | Track and report AI API spend. |
| IO-10 | Horizontal scaling for API tier | P3 | deferred | - | Multiple API instances behind load balancer. |

## Compliance & Security

| ID | Feature | Priority | Status | Phase | Notes |
|---|---|---|---|---|---|
| CS-01 | Encryption at rest (PostgreSQL, Qdrant) | P0 | planned | 7 | HIPAA requirement. |
| CS-02 | Encryption in transit (TLS 1.3) | P0 | planned | 7 | HIPAA requirement. |
| CS-03 | HIPAA compliance documentation | P0 | planned | 8 | PHI inventory, risk assessment, policies. |
| CS-04 | OWASP Top 10 security audit | P0 | planned | 8 | Standard web application security. |
| CS-05 | BAA template | P1 | planned | 8 | Legal template for customer agreements. |
| CS-06 | Data retention policies | P1 | planned | 8 | Configurable per-tenant retention periods. |
| CS-07 | Penetration testing | P1 | planned | 8 | External security assessment. |
| CS-08 | SOC 2 Type II preparation | P3 | deferred | - | Post-launch compliance certification. |
| CS-09 | HITRUST CSF assessment | P3 | deferred | - | Healthcare-specific security framework. |
