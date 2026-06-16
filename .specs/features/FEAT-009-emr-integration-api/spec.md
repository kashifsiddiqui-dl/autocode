# FEAT-009: EMR Integration API

## Status: Not Started
## Priority: P2
## Owner: TBD
## Estimated Effort: 0.5 weeks
## Depends On: FEAT-003, FEAT-007

---

## Summary

Expose a REST API designed for EMR (Electronic Medical Record) system integration. Supports API key authentication (in addition to SSO), webhook callbacks for asynchronous result delivery, and HL7 FHIR-formatted input/output for healthcare interoperability compliance.

## Problem Statement

Healthcare organizations need to integrate AI-assisted coding into their existing EMR workflows. EMR systems operate as server-side applications that require programmatic API access (not browser-based SSO), asynchronous processing patterns (webhook callbacks), and standardized data formats (HL7 FHIR). The integration API must be secure, reliable, and compliant with healthcare data exchange standards.

## Functional Requirements

### FR-1: API Key Authentication

- API keys issued per tenant, managed by tenant admins
- Key format: `ac_live_{random_64_chars}` (production) / `ac_test_{random_64_chars}` (sandbox)
- Keys sent via `Authorization: Bearer ac_live_...` header
- Key metadata: name, scopes, expiry date, created_by
- Key management endpoints:

```
# Create API key (admin only)
POST /api/v1/api-keys
Body: { "name": "Epic Integration", "scopes": ["coding:read", "coding:write"], "expires_in_days": 365 }
Response: { "key": "ac_live_...", "id": "uuid" }  // Key shown only once

# List API keys (admin only)
GET /api/v1/api-keys
Response: [{ "id": "uuid", "name": "...", "scopes": [...], "last_used_at": "...", "is_active": true }]

# Revoke API key (admin only)
DELETE /api/v1/api-keys/{id}
```

- Keys stored as bcrypt hashes (never stored in plaintext)
- Key lookup via prefix index (first 8 characters stored unencrypted for lookup)
- Scopes: `coding:read`, `coding:write`, `export:read`, `codes:read`

### FR-2: EMR Coding Endpoint

Simplified endpoint for EMR integration (synchronous response, no SSE):

```
POST /api/v1/emr/coding/analyze
Authorization: Bearer ac_live_...
Content-Type: application/json

Request Body:
{
  "clinical_text": "string (required)",
  "patient": {
    "mrn": "string (required for EMR)",
    "name": "string",
    "dob": "date",
    "gender": "string"
  },
  "options": {
    "max_results": 10,
    "min_confidence": 0.5,
    "standard": "icd10cm",
    "response_format": "json" | "fhir"
  },
  "callback_url": "https://emr.example.com/webhooks/coding (optional)"
}
```

**Synchronous Response (when no callback_url):**
```json
{
  "session_id": "uuid",
  "status": "completed",
  "duration_ms": 3200,
  "codes": [
    {
      "code": "E11.9",
      "system": "http://hl7.org/fhir/sid/icd-10-cm",
      "display": "Type 2 diabetes mellitus without complications",
      "confidence": 0.95,
      "is_billable": true
    }
  ]
}
```

**Asynchronous Response (when callback_url provided):**
```json
{
  "session_id": "uuid",
  "status": "processing",
  "callback_url": "https://emr.example.com/webhooks/coding",
  "estimated_completion_ms": 5000
}
```

### FR-3: Webhook Callbacks

When `callback_url` is provided in the request:

1. API returns immediately with `status: "processing"`
2. RAG pipeline runs asynchronously
3. On completion, POST results to the callback URL:

```
POST {callback_url}
Content-Type: application/json
X-AutoCode-Signature: sha256=...    # HMAC signature for verification
X-AutoCode-Event: coding.completed

Body:
{
  "event": "coding.completed",
  "session_id": "uuid",
  "timestamp": "2026-06-16T14:30:00Z",
  "data": {
    "status": "completed",
    "duration_ms": 3200,
    "codes": [...]
  }
}
```

Webhook reliability:
- Retry on failure: 3 attempts with exponential backoff (1s, 10s, 60s)
- Timeout: 10 seconds per attempt
- HMAC-SHA256 signature using a shared secret for payload verification
- Webhook event log for debugging (stored in database)

### FR-4: HL7 FHIR Input Support

Accept FHIR-formatted input:

```
POST /api/v1/emr/coding/analyze
Content-Type: application/fhir+json

Body:
{
  "resourceType": "Parameters",
  "parameter": [
    {
      "name": "clinicalNote",
      "valueString": "Patient presents with..."
    },
    {
      "name": "patient",
      "resource": {
        "resourceType": "Patient",
        "identifier": [{"value": "MRN-12345"}],
        "name": [{"family": "Doe", "given": ["John"]}],
        "birthDate": "1965-03-15",
        "gender": "male"
      }
    }
  ]
}
```

### FR-5: HL7 FHIR Output Support

When `response_format: "fhir"` is specified, return a FHIR Bundle:

```json
{
  "resourceType": "Bundle",
  "type": "collection",
  "entry": [
    {
      "resource": {
        "resourceType": "Condition",
        "code": {
          "coding": [{
            "system": "http://hl7.org/fhir/sid/icd-10-cm",
            "code": "E11.9",
            "display": "Type 2 diabetes mellitus without complications"
          }]
        },
        "subject": {"reference": "Patient/mrn-12345"}
      }
    }
  ]
}
```

### FR-6: Rate Limiting for API Keys

- Per-key rate limits configurable at key creation
- Default: 60 requests per minute
- Rate limit headers included in responses
- 429 response with Retry-After header when exceeded

### FR-7: Usage Tracking

- Track per-key usage: request count, last used timestamp, total codes generated
- Usage endpoint for admins:

```
GET /api/v1/api-keys/{id}/usage?period=30d
Response: { "requests": 1500, "codes_generated": 7800, "avg_latency_ms": 2800 }
```

## Non-Functional Requirements

- **Latency**: Synchronous response < 8 seconds (p95), accounting for no streaming
- **Reliability**: Webhook delivery guarantee: at-least-once with idempotency keys
- **Security**: API keys scoped to minimum required permissions, rotatable without downtime
- **Compliance**: HL7 FHIR R4 conformance for input and output
- **Availability**: API key validation < 5ms (Redis-cached)

## Acceptance Criteria

- [ ] API keys can be created, listed, and revoked by tenant admins
- [ ] API key authentication works for EMR coding endpoint
- [ ] Synchronous coding response returns complete results (no SSE)
- [ ] Webhook callback delivers results to callback URL on async requests
- [ ] Webhook retries on delivery failure (3 attempts with backoff)
- [ ] HMAC signature on webhook payload is verifiable
- [ ] FHIR-formatted input is accepted and parsed correctly
- [ ] FHIR-formatted output produces valid FHIR R4 Bundle
- [ ] Per-key rate limiting enforced
- [ ] Usage tracking records request count and last used timestamp
- [ ] API keys are stored as bcrypt hashes (verified by DB inspection)
- [ ] Revoking a key immediately prevents further access

## Test Plan

### Unit Tests
- Test API key generation and hashing
- Test HMAC signature generation and verification
- Test FHIR input parsing
- Test FHIR output generation
- Test rate limiting logic

### Integration Tests
- Test full EMR coding flow: authenticate with API key -> submit clinical text -> receive results
- Test webhook delivery with mock callback server
- Test webhook retry on callback failure
- Test FHIR input/output round-trip
- Test API key revocation blocks subsequent requests

### Security Tests
- Test invalid API key rejection
- Test expired API key rejection
- Test scope enforcement (key with `coding:read` cannot write)
- Test cross-tenant isolation with API keys
