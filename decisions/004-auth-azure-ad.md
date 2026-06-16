# ADR-004: Azure AD / Entra ID via OIDC for SSO Authentication

**Date:** 2026-06-16
**Status:** Accepted
**Deciders:** Engineering Team

## Context

Auto Code is a multi-tenant SaaS application serving healthcare organizations (hospitals, health systems, medical billing companies, physician practices). Authentication must satisfy several requirements:

1. **Enterprise SSO.** Healthcare organizations use centralized identity providers. Users should sign in with their existing organizational credentials, not create separate Auto Code accounts.
2. **Identity provider prevalence.** The majority of US healthcare organizations use Microsoft 365 / Azure AD (now Entra ID) as their identity provider. Epic, Cerner, and other EMR systems commonly integrate with Azure AD for identity federation.
3. **HIPAA compliance.** Authentication must support MFA enforcement (via the IdP), session management with appropriate timeouts, and audit logging of all authentication events.
4. **Multi-tenancy.** Each organization is a tenant. The authentication layer must identify which tenant a user belongs to and inject tenant context into every request for row-level security enforcement.
5. **Protocol simplicity.** The protocol should be well-supported in the Python/FastAPI ecosystem with minimal custom code.

## Decision

Use **Azure AD (Entra ID) as the primary identity provider** via the **OpenID Connect (OIDC)** protocol for SSO authentication.

### Implementation Architecture

```
Browser                     Auto Code API              Azure AD (Entra ID)
  |                             |                            |
  |  GET /login                 |                            |
  |  ----------------------->   |                            |
  |                             |  Redirect to /authorize    |
  |  <------ 302 -----------   |  (with PKCE challenge)     |
  |                             |                            |
  |  User authenticates at Azure AD (MFA if configured)      |
  |  -------------------------------------------------------->
  |                             |                            |
  |  <--- 302 with auth code ---|                            |
  |  ----------------------->   |                            |
  |                             |  POST /token               |
  |                             |  (code + PKCE verifier)    |
  |                             |  ------------------------->|
  |                             |  <-- id_token + access --- |
  |                             |                            |
  |                             |  Validate id_token (JWT)   |
  |                             |  Extract: sub, email,      |
  |                             |    tenant_id, roles        |
  |                             |                            |
  |                             |  Issue Auto Code tokens:   |
  |                             |    access (15min)          |
  |                             |    refresh (7d)            |
  |                             |                            |
  |  <-- Set-Cookie (tokens) -- |                            |
  |                             |                            |
  |  API requests with          |                            |
  |  Authorization: Bearer      |                            |
  |  ----------------------->   |                            |
  |                             |  Verify Auto Code JWT      |
  |                             |  Inject tenant context     |
  |                             |  Enforce RLS               |
```

### Technology Choices

| Component | Technology | Rationale |
|---|---|---|
| **OIDC Client** | `authlib` (Python) | Mature, well-maintained OIDC/OAuth2 library. Handles discovery, PKCE, token exchange, and JWKS validation. Preferred over `python-social-auth` (too heavy) and `msal` (Microsoft-specific, tighter coupling). |
| **JWT Handling** | `python-jose[cryptography]` | JWT creation, signing, and verification for Auto Code's own access/refresh tokens. RS256 signing with rotating key pairs. |
| **FastAPI Integration** | Custom `Depends()` middleware | `get_current_user` dependency that extracts and validates the Auto Code JWT, loads tenant context, and makes it available to every endpoint. |
| **Session Storage** | PostgreSQL `sessions` table | Refresh tokens stored server-side with user_id, tenant_id, expiry, device fingerprint. Enables revocation and audit. |

### Token Strategy

**Azure AD tokens** are used only during the OIDC flow (authorization code exchange). They are never stored long-term or sent to the frontend.

**Auto Code tokens** are issued after successful OIDC authentication:

| Token | Lifetime | Storage | Purpose |
|---|---|---|---|
| Access Token | 15 minutes | `HttpOnly`, `Secure`, `SameSite=Strict` cookie | API authentication. Short-lived to limit exposure window. |
| Refresh Token | 7 days | `HttpOnly`, `Secure`, `SameSite=Strict` cookie + server-side record | Silent token renewal. Rotated on each use (one-time use). |

Access token JWT claims:

```json
{
  "sub": "user-uuid",
  "email": "dr.smith@hospital.org",
  "tenant_id": "tenant-uuid",
  "tenant_slug": "general-hospital",
  "roles": ["coder", "admin"],
  "iss": "autocode",
  "iat": 1750089600,
  "exp": 1750090500
}
```

### Multi-Tenancy Integration

1. **Tenant registration.** When a new organization onboards, an admin registers their Azure AD tenant ID in Auto Code. This creates a tenant record with the Azure AD `tenant_id` (GUID) mapped to an Auto Code `tenant_id`.
2. **Login flow.** The OIDC authorization request includes the organization's Azure AD tenant ID in the `authority` URL (`https://login.microsoftonline.com/{azure_tenant_id}`), ensuring users authenticate against their own directory.
3. **Tenant resolution.** After OIDC token exchange, the `tid` (tenant ID) claim from the Azure AD id_token is matched to the Auto Code tenant record. If no match, authentication fails.
4. **Context injection.** The `tenant_id` is embedded in the Auto Code JWT. The FastAPI middleware extracts it and sets `request.state.tenant_id` on every request. All database queries use this for RLS filtering.
5. **Common endpoint.** A single `/login` endpoint can serve all tenants. The frontend passes an `organization_hint` parameter that determines which Azure AD tenant to authenticate against. Alternatively, tenant-specific login URLs (`/login/general-hospital`) resolve the Azure AD tenant ID from the slug.

### Role Mapping

Azure AD group memberships are mapped to Auto Code roles during authentication:

| Azure AD Group | Auto Code Role | Permissions |
|---|---|---|
| `AutoCode-Admins` | `admin` | Manage users, configure settings, view audit logs, manage LLM settings |
| `AutoCode-Coders` | `coder` | Submit coding queries, view results, export codes, view own history |
| `AutoCode-Reviewers` | `reviewer` | Review coding suggestions, approve/reject, add notes |
| `AutoCode-ReadOnly` | `readonly` | View coding results only, no submissions |

Group-to-role mapping is configurable per tenant (stored in the `tenant_role_mappings` table).

### Security Measures

- **PKCE (Proof Key for Code Exchange):** All OIDC flows use PKCE to prevent authorization code interception.
- **State parameter:** CSRF protection via cryptographically random state parameter validated on callback.
- **Nonce validation:** Prevents id_token replay attacks.
- **JWKS rotation:** Azure AD JWKS keys are cached with a 24-hour TTL and refreshed on key-not-found.
- **Refresh token rotation:** Each refresh token is single-use. Using a refresh token issues a new refresh token and invalidates the old one. If a revoked refresh token is presented, all sessions for that user are terminated (potential token theft).
- **Session revocation:** Admin can revoke all sessions for a user. User can revoke their own sessions on other devices.
- **Audit logging:** All authentication events (login, logout, token refresh, failed attempts, session revocation) are logged to the `auth_audit_log` table with timestamp, IP, user agent, and outcome.

## Alternatives Considered

### SAML 2.0
- **Rejected as primary protocol.** SAML is widely supported in healthcare but is significantly more complex to implement than OIDC. XML-based assertions, signature validation, and metadata exchange require heavy library support. OIDC achieves the same SSO functionality with simpler JSON-based tokens and REST endpoints.
- SAML support may be added later as a secondary option for organizations that require it (some legacy EMR integrations use SAML exclusively).

### Auth0 / Okta (Third-Party Auth Service)
- **Rejected.** Adds a SaaS dependency in the authentication path. While both support Azure AD federation, they introduce an additional hop and another vendor requiring a BAA. Direct OIDC integration with Azure AD is simpler, cheaper, and avoids sending authentication data through a third party.
- May reconsider if we need to support 10+ identity providers (Google Workspace, Okta, OneLogin, etc.) and the integration burden becomes excessive.

### Firebase Authentication
- **Rejected.** Google-centric, limited Azure AD integration, consumer-focused (not enterprise SSO). No HIPAA BAA available for Firebase Auth.

### Custom Username/Password Authentication
- **Rejected as primary auth.** Healthcare organizations expect SSO. Managing passwords, password policies, MFA, and credential storage is a liability. However, a fallback username/password option may be needed for small practices without Azure AD -- this would be implemented as a secondary auth method with mandatory MFA via TOTP.

### Microsoft Authentication Library (MSAL)
- **Rejected in favor of authlib.** MSAL is Microsoft's official library and tightly integrates with Azure AD, but it couples the application to Microsoft's authentication stack. `authlib` is provider-agnostic, making it easier to add support for other OIDC providers (Google Workspace, Okta) in the future without changing the core auth logic.

## Consequences

### Positive
- **Zero-friction onboarding for Azure AD organizations.** Users sign in with existing credentials. No new passwords to manage.
- **MFA enforcement delegated to IdP.** Azure AD conditional access policies handle MFA requirements. Auto Code does not need to implement MFA.
- **Tenant isolation from authentication.** Tenant context is established at login and enforced on every request. No cross-tenant data access is possible without a valid JWT for that tenant.
- **Audit trail.** Complete authentication event log for HIPAA compliance audits.
- **Future IdP flexibility.** `authlib`-based OIDC implementation can support additional providers (Google, Okta) with minimal code changes -- just add their OIDC discovery URLs and client credentials.

### Negative
- **Azure AD dependency.** If Azure AD has an outage, users cannot authenticate. Mitigation: existing sessions remain valid for their token lifetime (15 min access, 7 days refresh). Consider caching user identity for graceful degradation.
- **Configuration complexity per tenant.** Each tenant requires an Azure AD app registration on their side (or a multi-tenant app registration on ours). Onboarding documentation must be clear.
- **No offline access.** Users must be able to reach Azure AD to initially authenticate. Not suitable for air-gapped environments (rare in our target market).
- **Small practice gap.** Small physician practices may not have Azure AD. Need a fallback auth method for this segment (deferred to a later phase).

### Mitigations
- Provide step-by-step Azure AD app registration guide for tenant admins.
- Consider a multi-tenant Azure AD app registration to simplify onboarding (single app, all tenants consent).
- Implement username/password + TOTP as a secondary auth method in Phase 4 for organizations without Azure AD.
- Add session caching so users are not immediately locked out during short Azure AD outages.

## References

- [Microsoft Entra ID OIDC Documentation](https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols-oidc)
- [authlib Documentation](https://docs.authlib.org/en/latest/)
- [python-jose](https://github.com/mpdavis/python-jose)
- [HIPAA Security Rule - Access Control](https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html)
- [OAuth 2.0 PKCE (RFC 7636)](https://datatracker.ietf.org/doc/html/rfc7636)
