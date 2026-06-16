# FEAT-007: Multi-Tenant Authentication & Authorization

## Status: Not Started
## Priority: P1
## Owner: TBD
## Estimated Effort: 1 week
## Depends On: Architecture runway (DB schema with tenants, users tables)

---

## Summary

Implement multi-tenant authentication via Azure AD OIDC with JWT tokens, row-level security (RLS) for tenant data isolation, and role-based access control (RBAC) with three roles: admin, coder, and viewer. Includes tenant provisioning workflow and user management.

## Problem Statement

The medical coding platform serves multiple healthcare organizations. Each organization's data must be strictly isolated, users must authenticate through their organization's identity provider, and access must be controlled by role. HIPAA compliance requires audit-grade access controls and data separation.

## Functional Requirements

### FR-1: Azure AD OIDC Authentication

- **Authorization Code Flow with PKCE** for web application
- **Client Credentials Flow** for service-to-service (EMR integration)
- Configuration per tenant:
  - Azure AD Tenant ID
  - Client ID
  - Client Secret (stored encrypted)
  - Redirect URIs
- OIDC discovery via `https://login.microsoftonline.com/{tenant}/.well-known/openid-configuration`
- Token validation: signature, issuer, audience, expiry, nonce

### FR-2: JWT Token Management

**Access Token Claims:**
```json
{
  "sub": "azure-oid",
  "email": "user@org.com",
  "name": "User Name",
  "tenant_id": "uuid",
  "role": "coder",
  "iat": 1718550000,
  "exp": 1718553600
}
```

- Issue application JWT after Azure AD token validation
- Access token TTL: 1 hour
- Refresh token TTL: 24 hours (stored in HttpOnly secure cookie)
- Token refresh endpoint: `POST /api/v1/auth/refresh`
- Token revocation on logout: `POST /api/v1/auth/logout`
- Redis-backed token blacklist for revoked tokens

### FR-3: Row-Level Security (RLS)

- All tenant-scoped tables have `tenant_id` column
- PostgreSQL RLS policies enforce tenant isolation at the database level
- Application sets `app.current_tenant_id` session variable on each request
- RLS policies applied to: `coding_sessions`, `coding_results`, `users`, `api_keys`
- Superuser bypass for system-level operations (migrations, ingestion)

```sql
-- Set tenant context on each request
SET LOCAL app.current_tenant_id = '{tenant_uuid}';

-- RLS policy example
CREATE POLICY tenant_isolation ON coding_sessions
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);
```

### FR-4: Role-Based Access Control (RBAC)

| Role | Permissions |
|------|-------------|
| **admin** | Full access: manage users, manage settings, all coder permissions, view audit logs, manage API keys |
| **coder** | Coding workflow: create sessions, run analysis, accept/reject codes, export, browse codes |
| **viewer** | Read-only: view sessions and results, export, browse codes (cannot create sessions or modify results) |

Permission matrix:

| Action | admin | coder | viewer |
|--------|-------|-------|--------|
| Create coding session | Yes | Yes | No |
| Run coding analysis | Yes | Yes | No |
| Accept/reject codes | Yes | Yes | No |
| View sessions | Yes | Yes (own) | Yes (all) |
| Export session | Yes | Yes | Yes |
| Browse codes | Yes | Yes | Yes |
| Manage users | Yes | No | No |
| Manage API keys | Yes | No | No |
| View audit logs | Yes | No | No |
| Manage tenant settings | Yes | No | No |

### FR-5: Tenant Provisioning

- `POST /api/v1/admin/tenants` -- Create new tenant (system admin only)
- Request: `{ "name": "Org Name", "slug": "org-slug", "azure_tenant_id": "...", "default_standard": "icd10cm" }`
- Provisioning steps:
  1. Create tenant record in `tenants` table
  2. Create default admin user from provisioning request
  3. Set default coding standard
  4. Initialize tenant settings
- `GET /api/v1/admin/tenants` -- List all tenants (system admin only)
- `PATCH /api/v1/admin/tenants/{id}` -- Update tenant settings

### FR-6: User Management

- `GET /api/v1/users` -- List users in tenant (admin only)
- `POST /api/v1/users` -- Create user (admin only): `{ "email": "...", "name": "...", "role": "coder" }`
- `PATCH /api/v1/users/{id}` -- Update user role (admin only)
- `DELETE /api/v1/users/{id}` -- Deactivate user (admin only, soft delete)
- Auto-provisioning: First login from a known Azure AD tenant auto-creates user with default role

### FR-7: Auth Middleware

FastAPI dependency injection for authentication and authorization:

```python
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Validate JWT and return current user."""
    pass

async def require_role(required_role: str):
    """Dependency that checks user has required role."""
    pass

async def set_tenant_context(db: AsyncSession, user: User):
    """Set RLS tenant context on database session."""
    pass
```

## Non-Functional Requirements

- **Security**: All tokens encrypted in transit (TLS), refresh tokens in HttpOnly secure cookies
- **Compliance**: Audit log for all authentication events (login, logout, token refresh, failed attempts)
- **Performance**: Token validation < 10ms (cached JWKS)
- **Availability**: Graceful handling of Azure AD outages (cached tokens remain valid)

## Acceptance Criteria

- [ ] Users can authenticate via Azure AD OIDC and receive application JWT
- [ ] JWT contains tenant_id and role claims
- [ ] Token refresh works without re-authentication
- [ ] RLS prevents access to other tenants' data (verified by direct SQL query attempt)
- [ ] Admin role can manage users and tenant settings
- [ ] Coder role can perform full coding workflow but not manage users
- [ ] Viewer role can only view and export (cannot create sessions or modify codes)
- [ ] Tenant provisioning creates all necessary database records
- [ ] Auto-provisioning creates user on first login from known tenant
- [ ] Authentication events are logged to audit trail
- [ ] Token revocation on logout prevents token reuse

## Test Plan

### Unit Tests
- Test JWT creation and validation
- Test RBAC permission checks for each role
- Test tenant context setting

### Integration Tests
- Test Azure AD OIDC flow (with mock IdP)
- Test RLS isolation between tenants
- Test user management CRUD operations
- Test token refresh and revocation

### Security Tests
- Attempt cross-tenant data access (must fail)
- Attempt privilege escalation (coder accessing admin endpoints)
- Test expired token rejection
- Test revoked token rejection
- Test invalid signature rejection
