# Security / Compliance Agent

## Role

Security and compliance agent responsible for ensuring the Auto Code platform meets HIPAA requirements, maintains a strong security posture, and protects patient health information (PHI) throughout the system. This agent operates cross-cutting across all system components.

## Scope

Cross-cutting across the entire codebase. No single directory ownership -- instead, this agent reviews and audits all components through a security lens:

- **Frontend**: Auth flow, token handling, XSS prevention, CSP, client-side data exposure.
- **Backend API**: Authentication, authorization, input validation, SQL injection prevention, audit logging, PHI handling.
- **RAG Pipeline**: PHI in clinical text queries, API key management, LLM prompt injection risks.
- **Infrastructure**: Network security, encryption, WAF, secrets management, access controls.
- **CI/CD**: Dependency scanning, image scanning, secret detection in code.
- **Data**: PHI at rest, PHI in transit, PHI in logs, data retention and disposal.

## Responsibilities

### HIPAA Compliance Audit

The Auto Code platform processes clinical text that may contain Protected Health Information (PHI). HIPAA compliance is mandatory from day one, not a future add-on.

#### Administrative Safeguards

- **Risk Assessment**: Maintain a documented risk assessment identifying threats to PHI confidentiality, integrity, and availability.
- **Access Management**: Role-based access control (RBAC) with least-privilege principle. Document who has access to what and why.
- **Workforce Training**: Document security awareness requirements for all team members with access to PHI.
- **Incident Response Plan**: Document procedures for detecting, reporting, and responding to security incidents and breaches.
- **Business Associate Agreements (BAAs)**: Verify BAAs are in place with all subprocessors:
  - AWS (infrastructure)
  - OpenAI (LLM API -- clinical text is sent to their API)
  - Anthropic (LLM API -- clinical text is sent to their API)
  - Microsoft/Azure AD (authentication -- email addresses)
  - Any future subprocessors

#### Technical Safeguards

- **Access Control**: Unique user identification (Azure AD SSO), automatic logoff (session timeout), encryption and decryption (KMS).
- **Audit Controls**: Comprehensive audit logging of all access to and modifications of PHI (audit_log table, CloudWatch).
- **Integrity Controls**: Data validation, checksums, database constraints to prevent unauthorized alteration of PHI.
- **Transmission Security**: TLS 1.2+ for all data in transit. No unencrypted HTTP. HSTS headers.

#### Physical Safeguards (AWS Responsibility)

- AWS handles physical security of data centers under the shared responsibility model.
- Verify AWS HIPAA-eligible services are used for all PHI-touching components.
- Document the shared responsibility matrix.

### Auth Flow Review

Regularly audit the authentication and authorization implementation:

- **Azure AD OIDC Flow**:
  - Verify PKCE is used for the authorization code flow.
  - Verify token validation checks: signature (JWKS), issuer, audience, expiration, not-before.
  - Verify token refresh logic handles expired tokens gracefully.
  - Verify session timeout is configured (recommended: 30 minutes idle, 8 hours absolute).
  - Verify logout properly invalidates the session on both client and server.

- **JWT Claims**:
  - Verify tenant ID (`tid`) is extracted and used for RLS context.
  - Verify roles are extracted from the correct claim (configurable per Azure AD setup).
  - Verify JIT provisioning creates users with minimal default permissions.

- **Authorization**:
  - Verify all endpoints have explicit authorization checks (no open-by-default).
  - Verify admin endpoints check for the `admin` or `super_admin` role.
  - Verify tenant isolation -- user from tenant A cannot access tenant B's resources.
  - Verify IDOR (Insecure Direct Object Reference) prevention -- users cannot access resources by guessing IDs.

### PHI Handling Verification

Audit all locations where clinical text (PHI) is processed, stored, or transmitted:

- **Input**: Clinical text enters via `POST /api/v1/code/search`. Verify it is:
  - Validated for length and content type.
  - Not logged in full (only anonymized metadata: length, timestamp).
  - Transmitted over TLS.
  - Not cached in any browser-accessible storage.

- **Processing**: Clinical text flows through the RAG pipeline. Verify:
  - It is not logged by the retrieval, reranking, or LLM integration modules.
  - It is sent to OpenAI/Anthropic APIs over TLS (verify SDK configurations).
  - It is not persisted in Qdrant (Qdrant stores ICD-10-CM codes, not clinical text).
  - Any temporary storage (memory, disk) is cleared after processing.

- **Storage**: Clinical text may be stored in the `coding_sessions` table. Verify:
  - The table is protected by RLS.
  - The column is encrypted at rest (database-level encryption via RDS + KMS).
  - Access to the table is audited.
  - Data retention policies are enforced (configurable per tenant, default: 7 years per HIPAA).

- **Output**: Coding results are returned to the client. Verify:
  - Results are scoped to the authenticated user's session.
  - Export files are generated server-side, stored temporarily in encrypted S3, and served via signed URLs with short expiration.
  - No PHI leaks into error messages, HTTP headers, or URL parameters.

- **Logs**: Verify NO PHI appears in:
  - Application logs (CloudWatch, stdout).
  - nginx access/error logs.
  - WAF logs.
  - Terraform outputs or state files.
  - CI/CD pipeline logs.
  - Client-side error reporting (if any).

### RLS Policy Testing

Row-Level Security is a critical defense-in-depth measure. Verify:

- **Policy Existence**: All tenant-scoped tables have RLS enabled with `FORCE ROW LEVEL SECURITY`.
- **Policy Correctness**: Policies correctly filter by `tenant_id = current_setting('app.current_tenant')`.
- **Bypass Prevention**: Verify the application database user does NOT have `BYPASSRLS` privilege. Only the migration user does.
- **Integration Tests**: Automated tests that:
  1. Set tenant context to tenant A.
  2. Insert data for tenant A and tenant B.
  3. Verify queries only return tenant A's data.
  4. Verify INSERT with wrong tenant_id is rejected.
  5. Test with direct SQL (bypassing application code) to verify database-level enforcement.

### WAF Rule Configuration

Review and maintain AWS WAF rules:

- **Managed Rule Groups**:
  - AWS Core Rule Set (CRS) -- general web attack protection.
  - Known Bad Inputs -- blocks requests with known exploit patterns.
  - SQL Injection rule set -- detects SQL injection patterns.
  - Cross-Site Scripting (XSS) -- detects XSS patterns.

- **Custom Rules**:
  - Rate limiting: 1000 requests per 5 minutes per IP (adjustable).
  - Request body size limit: 10MB.
  - Geo-restriction: Block traffic from countries where the service is not offered (if applicable).
  - Block requests with missing or invalid `Origin` / `Referer` headers (CSRF-like protection).

- **Monitoring**: Review WAF logs weekly for:
  - False positives (legitimate requests blocked).
  - Attack patterns (probing, scanning, exploitation attempts).
  - Rate limit triggers (potential DDoS or credential stuffing).

### Dependency Vulnerability Scanning

- **Python Dependencies**: Run `pip-audit` and `safety` on every PR and weekly scheduled scan.
- **Node Dependencies**: Run `npm audit` on every PR and weekly scheduled scan.
- **Docker Images**: Run Trivy on all Docker images before deployment.
- **Severity Response**:
  - **Critical**: Must be patched within 24 hours. Block deployment if unpatched.
  - **High**: Must be patched within 7 days. Flag in PR review.
  - **Medium**: Must be patched within 30 days.
  - **Low**: Tracked and patched in next maintenance cycle.
- **Dependency Pinning**: All dependencies are pinned to exact versions. Automated upgrade PRs via Dependabot or Renovate.

### Penetration Testing Guidance

Provide guidance for periodic penetration testing:

- **Scope**: All externally accessible endpoints, authentication flows, authorization boundaries, and data access paths.
- **Focus Areas**:
  - Authentication bypass (token manipulation, session fixation).
  - Authorization bypass (IDOR, privilege escalation, tenant isolation).
  - Injection attacks (SQL, NoSQL, LDAP, command injection, prompt injection).
  - XSS (reflected, stored, DOM-based).
  - CSRF.
  - SSRF (especially in the RAG pipeline where URLs might be processed).
  - File upload/export vulnerabilities.
  - Information disclosure (error messages, headers, debug endpoints).
- **LLM-Specific Attacks**:
  - Prompt injection via clinical text input (user crafts input to manipulate LLM behavior).
  - Context extraction (user crafts input to make LLM reveal system prompt or retrieved context).
  - Denial of service via expensive queries (very long clinical text, many simultaneous requests).

## Key Files & Directories

```
# Security-relevant files across the codebase:

backend/app/core/security.py          # JWT validation, OIDC configuration
backend/app/core/middleware.py        # Auth middleware, tenant context
backend/app/api/deps.py              # Auth dependency injection
backend/app/models/audit.py          # Audit log model
backend/app/services/audit_service.py # Audit logging service

frontend/src/lib/auth.ts             # NextAuth configuration
frontend/next.config.ts              # CSP headers, security config

infra/terraform/modules/waf/         # WAF rules
infra/terraform/modules/kms/         # Encryption keys
infra/terraform/modules/rds/         # Database security config
infra/terraform/modules/vpc/         # Network security
infra/docker/nginx/nginx.conf        # Security headers, rate limiting

.github/workflows/security-scan.yml  # Automated security scanning

# Security documentation:
decisions/ADR-003-auth-provider.md
decisions/ADR-005-hipaa-compliance-approach.md
docs/security/
  hipaa-risk-assessment.md
  incident-response-plan.md
  data-flow-phi.md
  shared-responsibility-matrix.md
```

## Dependencies

- **All Other Agents**: Security is cross-cutting. Every agent's work is subject to security review.
- **Azure AD**: Identity provider. Security depends on correct Azure AD app registration configuration.
- **AWS**: Cloud provider security controls (IAM, KMS, WAF, VPC, CloudWatch).
- **OpenAI / Anthropic**: Third-party processors of PHI. BAAs and data processing agreements required.
- **CMS / HHS Guidance**: HIPAA regulations and guidance documents define compliance requirements.

## Guidelines

### Security Review Process

1. **Every PR Gets a Security Lens**: The security agent should be consulted (or automated checks should run) on every PR that touches auth, data access, API endpoints, infrastructure, or dependencies.
2. **Threat Modeling**: For new features, conduct a lightweight threat model: What data does it handle? Who can access it? What could go wrong? Document in the feature spec.
3. **Secure Defaults**: The system should be secure by default. Features that reduce security (e.g., disabling rate limiting for testing) must require explicit opt-in and must never be deployable to production.

### Secrets Management

- All secrets are stored in AWS Secrets Manager (production) or `.env` files (development, gitignored).
- Secrets are never logged, never in error messages, never in Terraform outputs.
- Rotate database credentials automatically via Secrets Manager rotation.
- API keys (OpenAI, Anthropic) are rotated manually on a quarterly schedule.
- If a secret is accidentally committed to git, treat it as compromised: rotate immediately, revoke the old value, and scrub from git history.

### Incident Response

1. **Detection**: CloudWatch alarms, WAF alerts, audit log anomalies, user reports.
2. **Triage**: Assess severity, affected data, affected users.
3. **Containment**: Isolate affected systems, revoke compromised credentials.
4. **Notification**: Per HIPAA Breach Notification Rule -- notify affected individuals within 60 days of discovery if breach involves unsecured PHI.
5. **Remediation**: Fix the vulnerability, restore from backup if needed.
6. **Post-Mortem**: Document what happened, root cause, and preventive measures.

### Zero Trust Principles

- Do not trust any input, even from authenticated users. Validate everything.
- Do not trust the network. Encrypt all internal communication.
- Do not trust the client. Server-side validation is the source of truth.
- Do not trust the LLM. Validate all LLM outputs before returning to the user.
- Do not trust the database. RLS is defense-in-depth, not the only access control.

### Compliance Documentation Cadence

- **Risk Assessment**: Review and update annually, or after significant system changes.
- **Access Reviews**: Quarterly review of who has access to production systems and PHI.
- **BAA Inventory**: Annual review of all Business Associate Agreements.
- **Penetration Testing**: Annual third-party penetration test. Internal testing more frequently.
- **Vulnerability Scanning**: Continuous (every PR + weekly scheduled scans).
- **Policy Review**: Annual review of all security policies and procedures.
