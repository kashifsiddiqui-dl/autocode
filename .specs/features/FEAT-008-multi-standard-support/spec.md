# FEAT-008: Multi-Standard Support

## Status: Not Started
## Priority: P2
## Owner: TBD
## Estimated Effort: 1 week
## Depends On: FEAT-001, FEAT-002

---

## Summary

Extend the platform to support multiple medical coding standards beyond ICD-10-CM. Implement an extensible `coding_standards` registry, standard-specific parsers and chunkers, standard-aware retrieval, and configurable per-tenant default standards. Initial focus is architecture extensibility; additional standards (CPT, ICD-10-PCS, SNOMED CT) will be added in future iterations.

## Problem Statement

Healthcare coding uses multiple classification systems depending on the context (diagnosis vs procedure, inpatient vs outpatient, US vs international). While ICD-10-CM is the initial focus, the platform must be architecturally ready to support additional standards without requiring fundamental changes to the ingestion pipeline, RAG system, or API layer.

## Functional Requirements

### FR-1: Coding Standards Registry

Database table for managing supported standards:

```sql
CREATE TABLE coding_standards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,           -- "ICD-10-CM", "CPT", "ICD-10-PCS", "SNOMED CT"
    version VARCHAR(20) NOT NULL,         -- "2026", "2025"
    display_name VARCHAR(255) NOT NULL,   -- "ICD-10-CM April 2026"
    description TEXT,
    effective_date DATE NOT NULL,
    expiry_date DATE,                     -- When this version is superseded
    source_format VARCHAR(50),            -- "xml", "csv", "rrf"
    source_files JSONB,                   -- List of source file paths
    chunk_types JSONB,                    -- Types of chunks generated
    total_codes INTEGER,                  -- Post-ingestion count
    total_chunks INTEGER,                 -- Post-ingestion count
    qdrant_collection VARCHAR(100),       -- Collection name in Qdrant
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(name, version)
);
```

### FR-2: Standard Registration API

```
# List all coding standards
GET /api/v1/standards
Response: [{ "id": "uuid", "name": "ICD-10-CM", "version": "2026", "is_active": true, ... }]

# Get standard details
GET /api/v1/standards/{id}
Response: Full standard record with ingestion statistics

# Register new standard (admin only)
POST /api/v1/standards
Body: { "name": "CPT", "version": "2026", "effective_date": "2026-01-01", ... }

# Update standard (admin only)
PATCH /api/v1/standards/{id}
Body: { "is_active": false }  // Deactivate old version
```

### FR-3: Standard-Specific Parser Interface

```python
class StandardParser(ABC):
    """Base class for coding standard parsers."""

    @abstractmethod
    def get_standard_info(self) -> StandardInfo:
        """Return metadata about this standard."""
        pass

    @abstractmethod
    def parse(self, source_files: list[Path]) -> list[CodeRecord]:
        """Parse source files into structured code records."""
        pass

    @abstractmethod
    def chunk(self, records: list[CodeRecord]) -> list[TextChunk]:
        """Generate text chunks optimized for embedding and retrieval."""
        pass

    @abstractmethod
    def validate(self, records: list[CodeRecord]) -> ValidationResult:
        """Validate parsed records for completeness."""
        pass
```

Registered parsers:

| Standard | Parser Class | Source Format | Status |
|----------|-------------|---------------|--------|
| ICD-10-CM | `ICD10CMParser` | XML (5 files) | Implemented (FEAT-001) |
| CPT | `CPTParser` | CSV/proprietary | Future |
| ICD-10-PCS | `ICD10PCSParser` | XML | Future |
| SNOMED CT | `SNOMEDParser` | RRF | Future |

### FR-4: Standard-Specific Chunking

Each standard requires different chunking strategies:

| Standard | Chunk Strategy |
|----------|---------------|
| ICD-10-CM | Hierarchy-aware chunks with includes/excludes context |
| CPT | Procedure description + guidelines + modifiers |
| ICD-10-PCS | 7-character axis-based chunks with device/approach context |
| SNOMED CT | Concept + relationships + hierarchy |

The chunker interface ensures consistent output format (text + metadata payload) regardless of the standard-specific strategy.

### FR-5: Standard-Aware Retrieval

- Each standard gets its own Qdrant collection (e.g., `icd10cm_chunks`, `cpt_chunks`)
- The `standard_id` metadata field enables filtering within shared collections if needed
- RAG pipeline accepts `standard` parameter to route queries to the correct collection
- Cross-standard queries are not supported (each analysis targets one standard)

### FR-6: Per-Tenant Default Standard

- Each tenant has a `default_standard_id` in the `tenants` table
- When a coding analysis request omits the `standard` parameter, use the tenant default
- Admins can change the default standard via tenant settings
- API supports explicit standard override per request

### FR-7: Standard Version Management

- Multiple versions of a standard can coexist (e.g., ICD-10-CM 2025 and 2026)
- Only one version per standard is "active" at a time
- Version transition workflow:
  1. Ingest new version data alongside existing
  2. Test new version with benchmark queries
  3. Activate new version (mark old as inactive)
  4. Old version data retained for historical reference

## Non-Functional Requirements

- **Extensibility**: Adding a new standard requires only implementing the parser interface (no core system changes)
- **Isolation**: Standards use separate Qdrant collections for performance isolation
- **Backward compatibility**: Existing ICD-10-CM functionality unaffected by multi-standard architecture

## Acceptance Criteria

- [ ] `coding_standards` table stores standard metadata and ingestion statistics
- [ ] Standards API supports CRUD operations (list, get, create, update)
- [ ] Parser interface is defined and ICD-10-CM parser conforms to it
- [ ] Chunker interface produces consistent output format across standards
- [ ] RAG pipeline routes queries to the correct Qdrant collection based on standard
- [ ] Per-tenant default standard is configurable and used when standard is not specified
- [ ] Multiple standard versions can coexist in the database
- [ ] Adding a stub parser for a new standard does not require changes to core pipeline code

## Test Plan

### Unit Tests
- Test standard registry CRUD operations
- Test parser interface compliance for ICD-10-CM parser
- Test standard routing in RAG pipeline

### Integration Tests
- Test ingestion with explicit standard parameter
- Test retrieval with standard-specific collection routing
- Test tenant default standard fallback

### Architecture Tests
- Create a mock/stub parser for a hypothetical standard
- Verify it integrates with the pipeline without core changes
- Verify separate Qdrant collection creation and isolation
