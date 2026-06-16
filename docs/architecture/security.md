# Auto Code - HIPAA Security Architecture

This document describes the security controls and HIPAA compliance measures implemented in the Auto Code platform.

---

## 1. Regulatory Context

Auto Code processes Protected Health Information (PHI) in the form of clinical documentation submitted for ICD-10-CM coding. As a SaaS application handling PHI on behalf of covered entities (hospitals, physician practices, billing companies), Auto Code operates as a **Business Associate** under HIPAA.

### Applicable Regulations

| Regulation | Relevance |
|---|---|
| HIPAA Privacy Rule (45 CFR 164.500-534) | Governs use and disclosure of PHI |
| HIPAA Security Rule (45 CFR 164.302-318) | Technical, administrative, and physical safeguards for ePHI |
| HIPAA Breach Notification Rule (45 CFR 164.400-414) | Breach detection, notification, and reporting requirements |
| HITECH Act | Extends HIPAA to Business Associates, strengthens penalties |
| State privacy laws | Applicable state-specific requirements (e.g., California CMIA, Texas HB 300) |

---

## 2. Encryption

### 2.1 Encryption at Rest

All data stores containing PHI or sensitive data are encrypted at rest using AES-256 encryption managed through AWS Key Management Service (KMS).

| Data Store | Encryption Method | Key Management |
|---|---|---|
| **RDS PostgreSQL** | AES-256 via RDS encryption (TDE) | AWS KMS Customer Managed Key (CMK) |
| **EBS Volumes** (EC2 instances) | AES-256 via EBS encryption | AWS KMS CMK |
| **S3 Buckets** (exports) | SSE-KMS (server-side encryption) | AWS KMS CMK, per-tenant key policy |
| **Redis** (session cache) | ElastiCache at-rest encryption | AWS managed key |
| **Qdrant** (vector DB) | EBS volume encryption | AWS KMS CMK |
| **CloudWatch Logs** | Log group encryption | AWS KMS CMK |
| **Secrets Manager** | Envelope encryption | AWS KMS CMK |

**Important**: Qdrant stores only ICD-10-CM reference data (code descriptions, index entries, drug/neoplasm tables). No PHI is stored in Qdrant. The vector database contains publicly available CMS classification data only.

### KMS Key Policy

```
 +---------------------------------------------------------------+
 | AWS KMS Customer Managed Key: "autocode-master-key"           |
 |                                                               |
 | Key Policy:                                                   |
 | - Key administrators: DevOps IAM role                         |
 | - Key users: Application IAM role, RDS service role           |
 | - Automatic rotation: Enabled (annual)                         |
 | - Deletion protection: 30-day waiting period                   |
 | - CloudTrail logging: All key usage events                    |
 |                                                               |
 | Grants:                                                       |
 | - RDS: Encrypt/Decrypt for database encryption                |
 | - EBS: Encrypt/Decrypt for volume encryption                  |
 | - S3: Encrypt/Decrypt for export file encryption              |
 | - CloudWatch: Encrypt/Decrypt for log encryption              |
 | - Secrets Manager: Encrypt/Decrypt for secret encryption      |
 +---------------------------------------------------------------+
```

### 2.2 Encryption in Transit

All data in transit is encrypted using TLS 1.2 or higher.

| Connection | Protocol | Certificate |
|---|---|---|
| Client <-> ALB | TLS 1.2+ (TLS 1.3 preferred) | ACM-managed certificate |
| ALB <-> nginx | TLS 1.2 (internal) | Self-signed internal CA |
| nginx <-> FastAPI | Localhost (127.0.0.1), no TLS needed | N/A (same host) |
| FastAPI <-> RDS | TLS 1.2 with `sslmode=verify-full` | RDS CA certificate |
| FastAPI <-> Qdrant | TLS 1.2 (gRPC with TLS) | Self-signed internal CA |
| FastAPI <-> Redis | TLS 1.2 (ElastiCache in-transit encryption) | AWS managed |
| FastAPI <-> LLM APIs | TLS 1.2+ | Provider-managed certificates |
| FastAPI <-> Azure AD | TLS 1.2+ | Microsoft-managed certificates |

### TLS Configuration (ALB)

```
 Security Policy: ELBSecurityPolicy-TLS13-1-2-2021-06
 
 Supported protocols: TLS 1.2, TLS 1.3
 Disabled protocols: SSLv3, TLS 1.0, TLS 1.1
 
 Cipher suites (TLS 1.2):
   - TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
   - TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
   - TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
   - TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
 
 Cipher suites (TLS 1.3):
   - TLS_AES_256_GCM_SHA384
   - TLS_AES_128_GCM_SHA256
   - TLS_CHACHA20_POLY1305_SHA256
 
 HSTS: Strict-Transport-Security: max-age=31536000; includeSubDomains
```

---

## 3. Authentication

### 3.1 Identity Provider: Azure AD (Entra ID)

Auto Code delegates identity management to Azure Active Directory using OpenID Connect (OIDC). This ensures:

- Enterprise-grade authentication managed by the customer's IT organization
- Multi-factor authentication (MFA) enforced by the customer's Azure AD policies
- Conditional Access policies (device compliance, network location) controlled by the customer
- Single Sign-On (SSO) with the customer's existing applications
- Centralized user provisioning and deprovisioning

### Azure AD Configuration

| Setting | Value |
|---|---|
| Protocol | OpenID Connect (OIDC) |
| Grant type | Authorization Code Flow with PKCE |
| Response type | `code` |
| Scopes | `openid`, `profile`, `email`, `offline_access` |
| Token endpoint auth | Client secret (stored in AWS Secrets Manager) |
| ID token claims | `sub`, `email`, `name`, `oid`, `tid` (tenant ID), `groups` |
| Redirect URI | `https://app.autocode.ai/api/v1/auth/callback` |
| Logout URI | `https://app.autocode.ai/api/v1/auth/logout` |
| Multi-tenant | Single-tenant per Azure AD app registration (one per customer) |

### 3.2 Application JWT Tokens

After validating the Azure AD ID token, the backend issues its own JWT tokens for subsequent API authentication.

#### Access Token

| Property | Value |
|---|---|
| Algorithm | RS256 (asymmetric RSA signing) |
| TTL | 15 minutes |
| Claims | `sub` (user UUID), `tenant_id`, `email`, `roles`, `permissions`, `iat`, `exp`, `iss` |
| Delivery | httpOnly, Secure, SameSite=Strict cookie |
| Signing key | RSA-2048 private key stored in AWS Secrets Manager |
| Validation key | RSA-2048 public key (JWKS endpoint for verification) |

#### Refresh Token

| Property | Value |
|---|---|
| TTL | 7 days |
| Storage | httpOnly, Secure, SameSite=Strict cookie (separate from access token) |
| Rotation | Enabled -- each refresh issues a new refresh token and revokes the old one |
| Revocation | Stored in PostgreSQL `refresh_tokens` table; revoked tokens are checked on each use |
| Family tracking | Refresh token family ID tracks lineage; if a revoked token is reused, entire family is revoked (replay detection) |

#### Token Security Measures

```
 +---------------------------------------------------------------+
 | Cookie Configuration                                          |
 |                                                               |
 | Set-Cookie: access_token=<JWT>;                               |
 |   HttpOnly;          <- Not accessible via JavaScript (XSS)   |
 |   Secure;            <- Only sent over HTTPS                  |
 |   SameSite=Strict;   <- Not sent with cross-site requests     |
 |   Path=/api;         <- Only sent to API endpoints            |
 |   Domain=.autocode.ai;                                        |
 |   Max-Age=900        <- 15 minutes                            |
 |                                                               |
 | Set-Cookie: refresh_token=<opaque>;                           |
 |   HttpOnly;                                                   |
 |   Secure;                                                     |
 |   SameSite=Strict;                                            |
 |   Path=/api/v1/auth/refresh;  <- Only sent to refresh endpt   |
 |   Domain=.autocode.ai;                                        |
 |   Max-Age=604800     <- 7 days                                |
 +---------------------------------------------------------------+
```

### 3.3 Session Management

| Control | Implementation |
|---|---|
| Session timeout (idle) | Access token expiry (15 min) acts as idle timeout; refresh extends |
| Session timeout (absolute) | Refresh token expiry (7 days) acts as absolute timeout |
| Concurrent sessions | Maximum 5 active refresh token families per user |
| Session termination | Logout revokes all refresh tokens for the user |
| Device tracking | User agent and IP stored with refresh token; alert on new device |

---

## 4. Authorization

### 4.1 Role-Based Access Control (RBAC)

Three primary roles with distinct permission sets:

```
 +-------------------------------------------------------------------+
 |                          ROLE HIERARCHY                            |
 |                                                                   |
 |  +------------------+                                             |
 |  |   ADMIN          |  Full access to all tenant resources         |
 |  |                  |  Can manage users, roles, settings           |
 |  |                  |  Can view all audit logs                     |
 |  |                  |  Can trigger data ingestion                  |
 |  +--------+---------+                                             |
 |           |                                                       |
 |  +--------v---------+                                             |
 |  |   CODER          |  Can submit coding requests                  |
 |  |                  |  Can accept/reject code suggestions          |
 |  |                  |  Can export own coding sessions              |
 |  |                  |  Can search codes                            |
 |  |                  |  Can view own audit trail                    |
 |  +--------+---------+                                             |
 |           |                                                       |
 |  +--------v---------+                                             |
 |  |   VIEWER         |  Can view coding sessions (read-only)        |
 |  |                  |  Can search codes (read-only)                |
 |  |                  |  Can view assigned audit reports             |
 |  |                  |  Cannot submit or modify coding requests     |
 |  +------------------+                                             |
 +-------------------------------------------------------------------+
```

### Permission Matrix

| Permission | Admin | Coder | Viewer |
|---|---|---|---|
| `code:read` | Yes | Yes | Yes |
| `code:write` | Yes | Yes | No |
| `code:delete` | Yes | No | No |
| `export:read` | Yes | Yes (own) | No |
| `export:write` | Yes | Yes | No |
| `audit:read` | Yes (all) | Yes (own) | Yes (assigned) |
| `user:read` | Yes | No | No |
| `user:write` | Yes | No | No |
| `settings:read` | Yes | Yes | Yes |
| `settings:write` | Yes | No | No |
| `ingestion:trigger` | Yes | No | No |

### 4.2 PostgreSQL Row-Level Security (RLS)

RLS provides defense-in-depth tenant isolation at the database level, independent of application logic.

#### RLS Implementation

```sql
-- Enable RLS on all tenant-scoped tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE coding_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE coding_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_settings ENABLE ROW LEVEL SECURITY;

-- Policy: users can only see rows belonging to their tenant
CREATE POLICY tenant_isolation_select ON coding_sessions
    FOR SELECT
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_insert ON coding_sessions
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_update ON coding_sessions
    FOR UPDATE
    USING (tenant_id = current_setting('app.current_tenant')::uuid)
    WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid);

CREATE POLICY tenant_isolation_delete ON coding_sessions
    FOR DELETE
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- Application sets tenant context on each request
-- (done in FastAPI TenantContextMiddleware)
SET app.current_tenant = '<tenant_id_from_jwt>';

-- Superuser bypass for admin operations (migrations, ingestion)
-- The app_admin role bypasses RLS for cross-tenant operations
ALTER TABLE coding_sessions FORCE ROW LEVEL SECURITY;
-- app_admin role is NOT subject to RLS (BYPASSRLS attribute)
```

#### RLS Verification

Regular automated tests verify RLS isolation:

1. Create two test tenants (A and B)
2. Insert data for both tenants
3. Set context to tenant A, attempt to query tenant B's data
4. Verify zero rows returned
5. Attempt INSERT with tenant B's ID while context is tenant A
6. Verify INSERT is rejected by WITH CHECK policy
7. Run these tests in CI/CD pipeline on every schema migration

---

## 5. PHI Handling

### 5.1 Data Classification

| Data Type | Classification | Storage Location | Encryption | Access Control |
|---|---|---|---|---|
| Clinical documentation text | **PHI** | PostgreSQL (coding_sessions) | AES-256 at rest, TLS in transit | RLS + RBAC |
| Patient age | **Limited PHI** | PostgreSQL (coding_sessions) | AES-256 at rest, TLS in transit | RLS + RBAC |
| Patient sex | **Limited PHI** | PostgreSQL (coding_sessions) | AES-256 at rest, TLS in transit | RLS + RBAC |
| ICD-10-CM codes (suggested) | **Non-PHI** (without patient link) | PostgreSQL | AES-256 at rest | RLS + RBAC |
| ICD-10-CM reference data | **Public data** | PostgreSQL + Qdrant | AES-256 at rest | No restrictions |
| User email/name | **PII** (not PHI unless linked to patient) | PostgreSQL | AES-256 at rest | RLS + RBAC |
| Audit logs | **May contain PHI references** | PostgreSQL + CloudWatch | AES-256 at rest | RLS + RBAC + append-only |
| Export files | **PHI** | S3 (time-limited) | SSE-KMS | Pre-signed URLs, RBAC |

### 5.2 LLM API Data Retention Policies

**This is a critical HIPAA control.** Clinical text is sent to LLM APIs for code reasoning. All LLM providers are configured for zero data retention.

| Provider | Model | Data Retention | BAA | API Configuration |
|---|---|---|---|---|
| **Anthropic** | Claude Sonnet/Opus | **Zero retention** -- no training, no logging of inputs/outputs | Yes (signed) | API key authentication, no data stored |
| **OpenAI** | GPT-4o, text-embedding-3-large | **Zero retention** -- opted out of training, API data not retained beyond 30 days for abuse monitoring (with BAA, 0 days) | Yes (signed) | Organization-level data retention set to 0 days |

**Verification measures**:
- Contractual: BAA terms explicitly prohibit use of PHI for model training
- Technical: API calls use organization-level settings that disable data retention
- Monitoring: Regular review of provider data handling policies and terms of service

### 5.3 Minimum Necessary Principle

The system limits PHI exposure to the minimum necessary for the coding function:

| Stage | Data Sent | Data NOT Sent |
|---|---|---|
| **Qdrant search** | Embedding vectors (not reversible to text) | No clinical text, no patient identifiers |
| **LLM API call** | Clinical text (for code reasoning), patient age range, patient sex | No patient name, no MRN, no DOB, no SSN, no address, no account number |
| **Audit logging** | SHA-256 hash of clinical text, suggested codes | No raw clinical text in audit logs |
| **Export files** | Coding results with clinical summary | Exported under user authorization, time-limited download |

### 5.4 PHI Input Sanitization

Before sending clinical text to LLM APIs, an optional PHI de-identification pass can be enabled:

1. **Pattern matching**: Detect and redact common PHI patterns (SSN, MRN, phone numbers, dates of birth)
2. **NER-based detection**: Named entity recognition to detect patient names, addresses, provider names
3. **Replacement**: Replace detected PHI with category tokens (e.g., "[PATIENT_NAME]", "[DATE_OF_BIRTH]")
4. **Preservation**: Medical terminology, condition descriptions, and clinical findings are preserved

Note: This is an optional layer. Some customers prefer to send unmodified clinical text to the LLM for maximum coding accuracy, relying on the zero-retention API configuration and BAA protections.

---

## 6. Audit Logging

### 6.1 Audited Events

Every action involving PHI access, system modification, or security-relevant operation is logged.

| Category | Events Logged |
|---|---|
| **Authentication** | Login success/failure, logout, token refresh, MFA challenge, session timeout |
| **PHI Access** | Coding request submitted, coding session viewed, clinical text accessed |
| **Coding Actions** | Code suggested, code accepted, code rejected, manual code added |
| **Export** | Export requested, generated, downloaded, expired |
| **Administration** | User created/modified/deactivated, role changed, settings modified |
| **Data Operations** | Ingestion started/completed, validation results |
| **Security** | Failed authorization, rate limit triggered, suspicious activity detected |

### 6.2 Audit Log Fields

Each audit log entry captures:

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Unique log entry identifier |
| `tenant_id` | UUID | Tenant context (RLS-protected) |
| `user_id` | UUID | Acting user |
| `action` | VARCHAR(100) | Action type (e.g., `coding_suggest`, `export_download`) |
| `resource_type` | VARCHAR(50) | Resource type (e.g., `coding_session`, `export`, `user`) |
| `resource_id` | UUID | Specific resource identifier |
| `details` | JSONB | Action-specific details (varies by action type) |
| `ip_address` | INET | Client IP address |
| `user_agent` | TEXT | Client user agent string |
| `request_id` | UUID | Correlation ID for the HTTP request |
| `created_at` | TIMESTAMPTZ | Timestamp (server time, UTC) |

### 6.3 Audit Log Integrity

```
 +---------------------------------------------------------------+
 | Immutability Controls                                         |
 |                                                               |
 | 1. Database permissions:                                      |
 |    - Application role: INSERT only (no UPDATE, DELETE)         |
 |    - Only audit_writer DB role can INSERT                     |
 |    - Trigger prevents UPDATE/DELETE even by superuser          |
 |                                                               |
 | 2. Table partitioning:                                        |
 |    - Monthly range partitions on created_at                   |
 |    - Old partitions marked read-only at filesystem level      |
 |                                                               |
 | 3. CloudWatch backup:                                         |
 |    - All audit events also sent to CloudWatch Logs            |
 |    - CloudWatch retention: 365 days                           |
 |    - Provides independent audit trail if DB is compromised    |
 |                                                               |
 | 4. Integrity verification:                                    |
 |    - Nightly job compares PostgreSQL audit count with          |
 |      CloudWatch log count                                     |
 |    - Alert on discrepancy > 0.1%                              |
 +---------------------------------------------------------------+
```

---

## 7. Network Security

### 7.1 VPC Architecture

```
 +---------------------------------------------------------------+
 |  VPC: 10.0.0.0/16                                             |
 |                                                               |
 |  +---------------------------+  +---------------------------+ |
 |  | Public Subnet: 10.0.1.0/24|  | Public Subnet: 10.0.2.0/24| |
 |  | (us-east-1a)              |  | (us-east-1b)              | |
 |  |                           |  |                           | |
 |  | ALB (internet-facing)     |  | NAT Gateway               | |
 |  | Internet Gateway          |  |                           | |
 |  +---------------------------+  +---------------------------+ |
 |                                                               |
 |  +---------------------------+  +---------------------------+ |
 |  | Private Subnet:10.0.10.0/24| | Private Subnet:10.0.20.0/24|
 |  | (us-east-1a)              |  | (us-east-1b)              | |
 |  |                           |  |                           | |
 |  | EC2: App servers          |  | EC2: App servers          | |
 |  | EC2: Qdrant               |  | EC2: Celery workers       | |
 |  | EC2: Redis                |  |                           | |
 |  +---------------------------+  +---------------------------+ |
 |                                                               |
 |  +---------------------------+  +---------------------------+ |
 |  | Data Subnet: 10.0.100.0/24|  | Data Subnet: 10.0.200.0/24|
 |  | (us-east-1a)              |  | (us-east-1b)              | |
 |  |                           |  |                           | |
 |  | RDS Primary               |  | RDS Standby (Multi-AZ)   | |
 |  +---------------------------+  +---------------------------+ |
 |                                                               |
 |  Route Tables:                                                |
 |  - Public: 0.0.0.0/0 -> Internet Gateway                    |
 |  - Private: 0.0.0.0/0 -> NAT Gateway (outbound only)        |
 |  - Data: No internet route (isolated)                        |
 +---------------------------------------------------------------+
```

### 7.2 Security Groups

| Security Group | Inbound Rules | Outbound Rules |
|---|---|---|
| **sg-alb** | 443/tcp from 0.0.0.0/0 (HTTPS) | 8080/tcp to sg-app (upstream) |
| **sg-app** | 8080/tcp from sg-alb only | 5432/tcp to sg-rds, 6333/tcp to sg-qdrant, 6379/tcp to sg-redis, 443/tcp to 0.0.0.0/0 (LLM APIs, Azure AD) |
| **sg-qdrant** | 6333/tcp, 6334/tcp from sg-app only | None (no outbound needed) |
| **sg-redis** | 6379/tcp from sg-app only | None |
| **sg-rds** | 5432/tcp from sg-app only | None |
| **sg-celery** | No inbound | 5432/tcp to sg-rds, 6379/tcp to sg-redis, 443/tcp to 0.0.0.0/0 (LLM APIs, S3) |

### 7.3 AWS WAF Configuration

WAF is attached to the ALB and provides Layer 7 protection.

| Rule Group | Purpose | Action |
|---|---|---|
| **AWSManagedRulesCommonRuleSet** | OWASP Top 10 protection (XSS, SQLi, path traversal) | Block |
| **AWSManagedRulesKnownBadInputsRuleSet** | Known malicious patterns (Log4j, etc.) | Block |
| **AWSManagedRulesSQLiRuleSet** | SQL injection patterns | Block |
| **AWSManagedRulesLinuxRuleSet** | Linux-specific exploits | Block |
| **Rate-based rule** | >2000 requests/5min from single IP | Block (5-min ban) |
| **Geo-blocking** | Block traffic from sanctioned countries | Block |
| **IP reputation** | AWS IP reputation list | Block |
| **Custom rule: large body** | Request body > 1MB | Block |

### 7.4 Additional Network Controls

| Control | Implementation |
|---|---|
| **VPC Flow Logs** | Enabled on all subnets, sent to CloudWatch Logs, 14-day retention |
| **DNS resolution** | VPC DNS resolution enabled, private DNS for RDS and ElastiCache |
| **VPC endpoints** | S3 gateway endpoint, KMS interface endpoint, CloudWatch interface endpoint (keeps traffic off public internet) |
| **Bastion host** | No bastion host; SSH access via AWS Systems Manager Session Manager only |
| **Network ACLs** | Default deny on data subnets; allow only from private subnets on database ports |

---

## 8. Business Associate Agreements (BAAs)

### 8.1 Required BAAs

| Vendor | Service | PHI Exposure | BAA Status |
|---|---|---|---|
| **AWS** | Infrastructure (RDS, EC2, S3, KMS, etc.) | PHI stored and processed on AWS infrastructure | Signed (AWS BAA addendum) |
| **Anthropic** | Claude API (LLM reasoning) | Clinical text sent for coding, zero retention | Signed |
| **OpenAI** | Embedding API, GPT-4o fallback | Clinical text embeddings and fallback reasoning | Signed |
| **Microsoft** | Azure AD (identity provider) | User identity data; no PHI in Azure AD | Signed (Microsoft BAA) |

### 8.2 Subcontractor BAAs

All subcontractors who may access PHI must have BAAs in place. The chain of responsibility:

```
 Covered Entity (Hospital)
      |
      | BAA
      v
 Auto Code (Business Associate)
      |
      +-- BAA --> AWS (Subcontractor BA)
      |
      +-- BAA --> Anthropic (Subcontractor BA)
      |
      +-- BAA --> OpenAI (Subcontractor BA)
      |
      +-- BAA --> Microsoft (Subcontractor BA)
```

### 8.3 BAA Review Schedule

- Annual review of all BAA terms
- Immediate review upon provider Terms of Service changes
- Re-assessment upon any provider security incident
- BAA status tracked in compliance management system

---

## 9. Incident Response

### 9.1 Incident Classification

| Severity | Description | Examples | Response Time |
|---|---|---|---|
| **Critical (P1)** | Confirmed PHI breach, system compromise, active attack | Unauthorized PHI access, data exfiltration, ransomware | Immediate (within 1 hour) |
| **High (P2)** | Potential PHI exposure, significant security vulnerability | Unpatched critical CVE, misconfigured access control, failed RLS | Within 4 hours |
| **Medium (P3)** | Security anomaly, policy violation, non-PHI incident | Suspicious login pattern, rate limit abuse, unauthorized admin action | Within 24 hours |
| **Low (P4)** | Minor security finding, informational | Failed login attempts below threshold, configuration drift | Within 72 hours |

### 9.2 Incident Response Procedure

```
 +---------------------------------------------------------------+
 | PHASE 1: DETECTION & TRIAGE (0-1 hours)                       |
 |                                                               |
 | Sources:                                                      |
 | - CloudWatch alarms (anomalous patterns)                      |
 | - WAF alerts (blocked attacks)                                |
 | - Audit log anomaly detection                                 |
 | - User-reported incidents                                     |
 | - AWS GuardDuty findings                                      |
 | - Vulnerability scan results                                  |
 |                                                               |
 | Actions:                                                      |
 | 1. Assess severity classification                             |
 | 2. Assign incident commander                                  |
 | 3. Begin incident log                                         |
 | 4. If P1: activate full incident response team                |
 +---------------------------------------------------------------+
                        |
                        v
 +---------------------------------------------------------------+
 | PHASE 2: CONTAINMENT (1-4 hours for P1)                       |
 |                                                               |
 | Short-term containment:                                       |
 | - Isolate affected systems (security group changes)           |
 | - Revoke compromised credentials/tokens                       |
 | - Block malicious IPs/users                                   |
 | - Preserve evidence (snapshots, logs)                         |
 |                                                               |
 | Long-term containment:                                        |
 | - Apply patches/fixes to prevent recurrence                   |
 | - Rotate all potentially compromised keys                     |
 | - Enable enhanced monitoring on affected systems              |
 +---------------------------------------------------------------+
                        |
                        v
 +---------------------------------------------------------------+
 | PHASE 3: ERADICATION (4-24 hours for P1)                      |
 |                                                               |
 | - Remove malware/unauthorized access                          |
 | - Patch vulnerabilities that were exploited                   |
 | - Rebuild compromised systems from clean images               |
 | - Verify RLS policies are intact                              |
 | - Verify encryption keys are not compromised                  |
 +---------------------------------------------------------------+
                        |
                        v
 +---------------------------------------------------------------+
 | PHASE 4: RECOVERY (24-72 hours for P1)                        |
 |                                                               |
 | - Restore systems to normal operation                         |
 | - Verify all security controls are functioning                |
 | - Enhanced monitoring for 30 days post-incident               |
 | - Validate data integrity                                     |
 +---------------------------------------------------------------+
                        |
                        v
 +---------------------------------------------------------------+
 | PHASE 5: NOTIFICATION (within 60 days of discovery for breach)|
 |                                                               |
 | If PHI breach confirmed (>500 individuals):                   |
 | - Notify HHS Office for Civil Rights within 60 days           |
 | - Notify affected individuals without unreasonable delay      |
 | - Notify prominent media outlets in affected states           |
 |                                                               |
 | If PHI breach (<500 individuals):                             |
 | - Log for annual report to HHS                                |
 | - Notify affected individuals without unreasonable delay      |
 |                                                               |
 | All breaches:                                                 |
 | - Notify affected covered entities (tenants) immediately      |
 | - Provide breach details: what PHI was involved, what         |
 |   happened, what we are doing, what they should do            |
 +---------------------------------------------------------------+
                        |
                        v
 +---------------------------------------------------------------+
 | PHASE 6: POST-INCIDENT REVIEW (within 2 weeks)               |
 |                                                               |
 | - Root cause analysis                                         |
 | - Timeline reconstruction                                     |
 | - Lessons learned                                             |
 | - Policy/procedure updates                                    |
 | - Security control improvements                               |
 | - Update incident response plan                               |
 +---------------------------------------------------------------+
```

### 9.3 Automated Detection and Alerting

| Alert | Trigger | Severity | Response |
|---|---|---|---|
| Failed login spike | >10 failed logins per user in 5 minutes | High | Lock account, alert security team |
| Cross-tenant access attempt | RLS policy violation logged | Critical | Alert security team, investigate |
| Unusual export volume | >10 exports per user in 1 hour | Medium | Alert admin, review exports |
| Admin role escalation | Role changed to admin outside business hours | High | Alert security team, require confirmation |
| API rate limit abuse | Sustained rate limit triggering from single user | Medium | Alert admin, review usage |
| WAF attack pattern | >100 blocked requests from single IP in 5 minutes | High | Auto-block IP, alert security team |
| LLM API key exposure | API key pattern detected in logs or code | Critical | Rotate key immediately, alert security team |
| Database connection anomaly | Connection from unauthorized IP to RDS | Critical | Block connection, alert security team |

---

## 10. Data Retention Policies

### 10.1 Retention Schedule

| Data Category | Retention Period | Disposal Method | Rationale |
|---|---|---|---|
| **Coding sessions** (clinical text + results) | 7 years from creation | Secure delete (overwrite + drop partition) | HIPAA: 6 years from date of creation or last effective date |
| **Audit logs** | 7 years | Partition drop | HIPAA audit trail requirement |
| **Export files** (S3) | 90 days | S3 lifecycle auto-delete | Temporary artifacts; regeneratable from source data |
| **User accounts** | Duration of employment + 90 days | Soft delete, then hard delete | Access revocation on termination |
| **Refresh tokens** | 7 days (active), 30 days (revoked records) | Hard delete | Security hygiene |
| **ICD-10-CM reference data** | Indefinite (versioned) | Not deleted; old versions archived | Reference data, not PHI |
| **Application logs** (CloudWatch) | 365 days | CloudWatch auto-expiry | Operational troubleshooting |
| **VPC Flow Logs** | 14 days | CloudWatch auto-expiry | Network forensics |
| **Database backups** (RDS) | 35 days (automated), 1 year (manual snapshots) | RDS auto-delete for automated, manual review for snapshots | Disaster recovery |

### 10.2 Data Disposal Procedures

1. **PostgreSQL data**: Monthly automated job identifies records past retention period. Records are deleted in batches during off-peak hours. For partitioned tables (audit_logs), entire partitions are dropped.

2. **S3 objects**: S3 lifecycle rules automatically transition objects to Glacier after 30 days and delete after 90 days. Deletion is permanent (no versioning recovery after lifecycle rule applies).

3. **Backups**: RDS automated backups expire per retention window. Manual snapshots are reviewed quarterly and deleted if past retention period. EBS snapshots follow the same schedule.

4. **Disposal verification**: Monthly automated report compares record counts against retention policy. Any records past retention period that are not yet disposed trigger an alert.

### 10.3 Right to Deletion

If a tenant (covered entity) requests deletion of their data:

1. Verify authorization (written request from authorized representative)
2. Export all tenant data for the tenant's records (if requested)
3. Delete all tenant-scoped records from PostgreSQL (CASCADE from tenants table)
4. Delete all S3 objects under the tenant's prefix
5. Audit logs for the tenant are retained for the full retention period (legal requirement)
6. Verify deletion completeness with automated checks
7. Issue deletion confirmation certificate

---

## 11. Vulnerability Management

### 11.1 Scanning Schedule

| Scan Type | Frequency | Tool | Scope |
|---|---|---|---|
| Dependency vulnerability scan | Every commit (CI/CD) | Dependabot / pip-audit / npm audit | Python + Node.js dependencies |
| Container image scan | Every build | AWS ECR image scanning / Trivy | Docker images |
| Infrastructure scan | Weekly | AWS Inspector | EC2 instances, RDS |
| Web application scan | Monthly | OWASP ZAP (automated) | API endpoints |
| Penetration test | Annually | Third-party security firm | Full application + infrastructure |
| Code security review | Every PR | CodeQL / Semgrep | Application code |

### 11.2 Patch Management

| Severity | Patching SLA | Process |
|---|---|---|
| Critical (CVSS 9.0+) | 24 hours | Emergency patch, off-cycle deployment |
| High (CVSS 7.0-8.9) | 7 days | Priority patch, next deployment window |
| Medium (CVSS 4.0-6.9) | 30 days | Standard patch cycle |
| Low (CVSS 0.1-3.9) | 90 days | Next quarterly update |

---

## 12. Security Training and Awareness

| Audience | Training | Frequency |
|---|---|---|
| All employees | HIPAA awareness, phishing prevention | Annual + onboarding |
| Development team | Secure coding practices, OWASP Top 10 | Semi-annual |
| Operations team | Incident response procedures, key management | Semi-annual |
| Security team | Advanced threat detection, forensics, HIPAA Security Rule | Quarterly |

---

## 13. Compliance Monitoring

### 13.1 Ongoing Compliance Activities

| Activity | Frequency | Owner |
|---|---|---|
| Risk assessment | Annual | Security Officer |
| Policy review | Annual | Compliance Officer |
| Access review (user permissions) | Quarterly | Admin + Security |
| BAA review | Annual | Legal + Compliance |
| Incident response drill | Semi-annual | Security team |
| Backup restoration test | Quarterly | Operations |
| RLS policy verification | Monthly (automated) | Engineering |
| Encryption verification | Monthly (automated) | Operations |
| Audit log integrity check | Nightly (automated) | Operations |

### 13.2 Documentation Maintained

| Document | Purpose | Review Cycle |
|---|---|---|
| Security Risk Assessment | HIPAA 164.308(a)(1) | Annual |
| Security Policies and Procedures | HIPAA 164.316(a) | Annual |
| Business Associate Agreements | HIPAA 164.502(e) | Annual |
| Incident Response Plan | HIPAA 164.308(a)(6) | Semi-annual |
| Disaster Recovery Plan | HIPAA 164.308(a)(7) | Annual |
| Workforce Training Records | HIPAA 164.308(a)(5) | Ongoing |
| Audit Log Reports | HIPAA 164.312(b) | Monthly |
| Access Authorization Records | HIPAA 164.308(a)(4) | Quarterly |
