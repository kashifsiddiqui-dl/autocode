# ADR-001: Use Qdrant (Self-Hosted) as Vector Database

**Date:** 2026-06-16
**Status:** Accepted
**Deciders:** Engineering Team

## Context

Auto Code is a RAG-based medical coding assistant that needs a vector database to store and query approximately 130,000 medical code embeddings derived from the ICD-10-CM classification system. The vector store must support:

1. **Rich metadata filtering** - Codes are organized by chapter (A00-B99, C00-D49, etc.), section, billable status, and hierarchical depth. Queries must filter by these dimensions before or during vector search to reduce the candidate set and improve relevance.
2. **Multiple embedding representations** - Each code has a human-readable description (e.g., "Type 2 diabetes mellitus with diabetic chronic kidney disease") and dense clinical context (includes/excludes notes, coding instructions, parent chain context). These serve different retrieval needs and should be searchable independently.
3. **Hybrid search** - Clinical notes use varied terminology. Sparse keyword matching (BM25-style) combined with dense semantic search yields significantly better recall than either alone, especially for exact code identifiers and abbreviations.
4. **HIPAA compliance** - The system will process Protected Health Information (PHI). The vector database must run on infrastructure we control; sending PHI to a third-party SaaS vector database requires a Business Associate Agreement and introduces data residency risk.
5. **Production reliability** - Persistence, snapshotting, horizontal scaling, and collection-level isolation for multi-tenant deployments.

## Decision

Use **Qdrant** (self-hosted, containerized via Docker) as the vector database.

### Key Capabilities Driving This Decision

| Capability | Qdrant Support | Why It Matters |
|---|---|---|
| **Self-hosted deployment** | Docker image, Helm chart, bare-metal binary | PHI stays on our infrastructure; no BAA required for the vector layer |
| **Named vectors** | Multiple named vector spaces per point | Store `description` (OpenAI 1024d) and `clinical_context` (PubMedBERT 768d) as separate named vectors on the same point |
| **Native sparse vectors** | Built-in sparse vector support with SPLADE/BM25 | Hybrid search without a separate Elasticsearch/BM25 sidecar |
| **Payload filtering** | Indexed payload fields with conditions | Filter by `chapter`, `section`, `is_billable`, `code_type`, `hierarchy_depth` before ANN search |
| **Persistence + snapshots** | WAL-based persistence, full/incremental snapshots | Crash recovery and point-in-time backup for compliance |
| **Collection isolation** | Separate collections with independent config | One collection per tenant or per code system version |
| **gRPC + REST APIs** | Both available | gRPC for high-throughput ingestion, REST for debugging |
| **Quantization** | Scalar and product quantization | Reduce memory footprint for 130K vectors without meaningful recall loss |

### Qdrant Collection Schema (Planned)

```
Collection: icd10cm_april_2026
  Named vectors:
    - description: float32[1024] (text-embedding-3-large)
    - clinical_context: float32[768] (PubMedBERT)
    - sparse_text: sparse vector (BM25 token weights)
  Payload fields (indexed):
    - code: keyword (e.g., "E11.22")
    - code_type: keyword (billable_code | category | subcategory | index_entry | drug_entry | neoplasm_entry)
    - chapter: keyword (e.g., "4" for Endocrine)
    - section: keyword (e.g., "E08-E13")
    - is_billable: bool
    - hierarchy_depth: integer
    - parent_code: keyword
    - has_7th_char: bool
    - source_file: keyword
  Payload fields (not indexed, stored):
    - description: text
    - full_context: text (inherited parent chain, includes, excludes)
    - excludes1: text[]
    - excludes2: text[]
    - code_first: text
    - use_additional: text
    - inclusion_terms: text[]
    - seventh_char_definitions: json
```

## Alternatives Considered

### Pinecone
- **Rejected.** Fully managed SaaS only. All vectors and payloads are stored on Pinecone's infrastructure. Even with a BAA, sending PHI-adjacent clinical text embeddings to a third-party service adds data residency risk and complicates compliance audits. No self-hosted option exists.
- Does not support named vectors (would need separate indexes for description vs. clinical context, doubling costs and complicating queries).
- No native sparse vector support (would need a hybrid search workaround).

### ChromaDB
- **Rejected.** Designed for prototyping and development. Single-node architecture with no production clustering story. No native sparse vectors. Metadata filtering is basic (no indexed payload fields). Persistence is SQLite-backed, not suitable for production workloads with 130K+ points and concurrent query load.
- Would be appropriate for a local development/testing mock but not for production.

### pgvector (PostgreSQL Extension)
- **Rejected.** While we already plan to use PostgreSQL for relational data (tenants, users, audit logs), pgvector has significant limitations for this use case:
  - No sparse vector support (no hybrid search without a separate system).
  - Limited metadata filtering performance (SQL WHERE clauses on JSONB are slower than Qdrant's indexed payloads for high-cardinality filtering during ANN search).
  - No named vectors (cannot store multiple embedding types on the same row efficiently for independent search).
  - ANN index performance (HNSW via pgvector) is competitive but query planning with complex filters is less predictable than Qdrant's purpose-built filterable HNSW.
- pgvector remains a fallback if we need to simplify infrastructure at the cost of search quality.

### Weaviate
- **Rejected.** Capable self-hosted vector database with good filtering and hybrid search. However:
  - Heavier operational footprint (Java-based modules, more complex configuration).
  - Module-based architecture adds deployment complexity (text2vec modules, etc.).
  - Named vectors are supported but the API is more opinionated about schema.
  - Community is smaller than Qdrant's for Python/FastAPI ecosystems.
  - Not a strong differentiator over Qdrant for our specific requirements.

## Consequences

### Positive
- **Full data sovereignty.** All vector data, payloads, and embeddings stay on infrastructure we control. Simplifies HIPAA compliance posture.
- **Single system for hybrid search.** Dense + sparse vectors in one collection eliminates the need for a separate BM25 engine (Elasticsearch/OpenSearch), reducing operational complexity.
- **Named vectors enable flexible retrieval.** Can search by description similarity, clinical context similarity, or both, with independent scoring and late fusion.
- **Payload filtering reduces search space.** Filtering by chapter, billable status, or code type before ANN search improves both speed and relevance.
- **Snapshot-based backup.** Point-in-time snapshots enable versioned backups and disaster recovery without custom export tooling.

### Negative
- **Operational overhead.** Self-hosting Qdrant means we own uptime, upgrades, and monitoring. Must set up health checks, disk alerts, and backup schedules.
- **Infrastructure cost.** Qdrant requires dedicated compute and memory. For 130K vectors at 1024d + 768d + sparse, estimated memory footprint is ~2-3 GB (with scalar quantization), but we need headroom for growth.
- **Team learning curve.** Team has more experience with PostgreSQL than purpose-built vector databases. Qdrant's API and configuration (HNSW params, quantization settings, optimizers) require learning.
- **Version coupling.** Qdrant is evolving rapidly. Collection schema migrations between major versions may require re-ingestion.

### Mitigations
- Use Docker Compose for local dev, Helm chart for production Kubernetes deployment.
- Implement health check endpoints and Prometheus metrics from day one.
- Maintain a re-ingestion pipeline so collections can be rebuilt from source XML in under 30 minutes.
- Pin Qdrant version in infrastructure config and test upgrades in staging before production.

## References

- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Qdrant Named Vectors](https://qdrant.tech/documentation/concepts/vectors/#named-vectors)
- [Qdrant Sparse Vectors](https://qdrant.tech/documentation/concepts/vectors/#sparse-vectors)
- [Qdrant Filtering](https://qdrant.tech/documentation/concepts/filtering/)
- [HIPAA Security Rule - Technical Safeguards](https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html)
