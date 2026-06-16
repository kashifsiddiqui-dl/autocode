# ADR-003: Dual Embedding Strategy with Named Vectors

**Date:** 2026-06-16
**Status:** Accepted
**Deciders:** Engineering Team

## Context

Auto Code's RAG pipeline must retrieve the most relevant ICD-10-CM codes given a clinician's natural-language description of a patient's condition. The embedding model choice directly impacts retrieval quality, which is the primary determinant of coding accuracy.

Medical coding search has two distinct retrieval needs:

1. **Description matching** - The user describes a condition ("patient has type 2 diabetes with kidney complications") and we need to find codes whose descriptions semantically match. This is a general semantic similarity task where broad, high-quality language models excel.

2. **Clinical context matching** - The user's query may reference clinical nuances that appear not in code descriptions but in the surrounding context: includes notes, excludes notes, coding instructions, parent hierarchy context. This text uses dense medical terminology and abbreviations. Domain-specific biomedical models outperform general models on this text type.

A single embedding model cannot optimally serve both needs. General models (OpenAI, Cohere) handle description matching well but underperform on dense clinical text. Biomedical models (PubMedBERT, BioLinkBERT) excel on clinical terminology but may miss colloquial or lay-language queries.

Qdrant's **named vectors** feature (ADR-001) enables storing multiple embedding representations per point and searching them independently or in combination, making a dual-model approach architecturally clean.

## Decision

Use a **dual embedding strategy** with two named vectors per chunk:

### 1. Description Vector: OpenAI `text-embedding-3-large` (1024 dimensions)

- **Input text:** Code description, index term, or substance name -- the primary human-readable identifier.
- **Dimensionality:** 1024 (reduced from native 3072 via OpenAI's built-in dimension reduction with `dimensions=1024`). The 1024d variant retains ~99.5% of the retrieval quality of the full 3072d at 1/3 the storage and search cost.
- **Why this model:**
  - State-of-the-art on MTEB benchmarks for general semantic similarity.
  - Handles both formal medical terminology ("Type 2 diabetes mellitus with diabetic chronic kidney disease") and informal/lay language ("sugar diabetes with kidney problems") effectively.
  - Matryoshka representation learning enables dimension reduction without re-embedding.
  - Well-supported API with high throughput (batch embedding up to 2048 inputs per request).
  - Deterministic outputs for the same input (important for caching and reproducibility).

### 2. Clinical Context Vector: PubMedBERT (`microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext`, 768 dimensions)

- **Input text:** Full clinical context -- includes notes, excludes notes, Code First/Use Additional directives, parent chain descriptions, 7th character definitions.
- **Dimensionality:** 768 (native BERT-base dimension).
- **Why this model:**
  - Pre-trained on PubMed abstracts and PMC full-text articles. Vocabulary and attention patterns are optimized for biomedical text.
  - Outperforms general BERT and sentence-transformers on biomedical NER, relation extraction, and sentence similarity tasks (BLURB benchmark).
  - Understands medical abbreviations, Latin terms, anatomical references, and drug names that appear in ICD-10-CM context notes.
  - Self-hosted (runs locally via `transformers` + `torch`). No API calls, no per-token cost, no PHI exposure.
  - 768d is compact enough for 130K vectors to fit comfortably in memory (~400 MB).

### 3. Sparse Vector: BM25 Token Weights

- **Input text:** Combined description + clinical context (concatenated).
- **Implementation:** Custom BM25 tokenizer with IDF weights computed over the full 130K chunk corpus, stored as Qdrant sparse vectors.
- **Purpose:** Exact-match keyword retrieval for code identifiers (e.g., "E11.22"), abbreviations ("DM2"), and specific terms that semantic search may miss.

### Search Strategy

At query time, searches are executed across all three vector types and results are fused:

```
Query: "type 2 diabetes with chronic kidney disease"

1. Dense search on `description` vector (OpenAI embedding of query)
   -> Top 20 by cosine similarity

2. Dense search on `clinical_context` vector (PubMedBERT embedding of query)
   -> Top 20 by cosine similarity

3. Sparse search on BM25 vector
   -> Top 20 by dot product

4. Reciprocal Rank Fusion (RRF) across all three result sets
   -> Re-ranked top 10 returned to LLM
```

Payload filters (chapter, billable status, code type) are applied within each search to narrow the candidate set before ANN traversal.

### Embedding Pipeline Architecture

```
XML Source Files
      |
      v
  Chunk Builder (ADR-002)
      |
      v
  +---+---+
  |       |
  v       v
OpenAI  PubMedBERT    BM25 Tokenizer
 API     (local)       (local)
  |       |               |
  v       v               v
description  clinical_context  sparse_text
 [1024d]      [768d]           [sparse]
  |           |                |
  +-----+-----+-------+-------+
        |
        v
    Qdrant Upsert
    (named vectors + payload)
```

## Alternatives Considered

### Single Model: OpenAI `text-embedding-3-large` Only
- **Rejected as sole model.** Excellent for description matching but suboptimal for dense clinical context. Tested with ICD-10-CM excludes notes containing terms like "sequela" and "underdosing" -- general models sometimes conflate these with lay-language equivalents. Also, every query and chunk requires an API call, creating a cost and latency dependency.

### Single Model: PubMedBERT Only
- **Rejected as sole model.** Excels on clinical terminology but has a 512-token context window (BERT limitation), which is too short for some assembled chunk texts. Also underperforms on informal/lay-language queries that clinicians sometimes use. No API cost, but lacks the broad language understanding of larger models.

### Cohere `embed-v3` (Multilingual)
- **Considered.** Strong multilingual support and input-type-aware embeddings (search_document vs. search_query). However, the multilingual capability is unnecessary (ICD-10-CM is English-only in this deployment), and it is a SaaS API with the same PHI concerns as OpenAI for the clinical context vectors. Does not offer a meaningful advantage over OpenAI for English medical text.

### BGE-M3 (BAAI)
- **Considered.** Open-source model with native dense + sparse + ColBERT multi-vector output. Would simplify the pipeline by using one model for all three representations. However, it is not domain-specialized for biomedical text, and its sparse representations are not as well-tested as dedicated BM25 for exact-match medical term retrieval. Remains a candidate for future evaluation.

### Fine-tuned Model on ICD-10-CM Data
- **Deferred.** Fine-tuning a sentence-transformer on ICD-10-CM code-description pairs would likely improve retrieval quality. However, this requires a labeled dataset of (query, relevant_code) pairs that we do not yet have. Plan to collect query-result feedback data from production usage and fine-tune in a later phase.

## Consequences

### Positive
- **Best-of-both-worlds retrieval.** General model catches broad/informal queries; domain model catches clinical nuance. Hybrid sparse search catches exact terms. RRF fusion ensures robust ranking.
- **Independent scoring allows tuning.** Can adjust the weight of description vs. clinical_context vs. sparse results in the fusion step without re-embedding.
- **Clinical context vectors are self-hosted.** PubMedBERT runs locally -- no API cost for 130K clinical context embeddings, and no PHI exposure for context text.
- **Dimension reduction saves resources.** 1024d (OpenAI) + 768d (PubMedBERT) = 1792d total per point. With scalar quantization, ~130K points require ~1-2 GB memory, well within a single-node Qdrant deployment.

### Negative
- **Two embedding models = two systems to maintain.** OpenAI API dependency for description embeddings (cost, rate limits, version changes). PubMedBERT requires GPU or CPU inference infrastructure.
- **Embedding cost for OpenAI.** ~130K chunks at ~100 tokens average = ~13M tokens. At $0.13/1M tokens (text-embedding-3-large), initial ingestion costs ~$1.70. Query-time embedding costs are negligible. Annual re-ingestion is also cheap.
- **Query latency.** Three parallel searches (two dense + one sparse) add latency compared to a single search. Mitigated by running searches concurrently and using Qdrant's batch search API.
- **RRF tuning required.** The relative weighting of three result sets needs empirical tuning. Initial weights: description=1.0, clinical_context=0.8, sparse=0.6 (subject to A/B testing).

### Mitigations
- Cache OpenAI embeddings by content hash. Unchanged chunks are never re-embedded.
- Run PubMedBERT inference on CPU (adequate for batch ingestion; ~2 hours for 130K chunks). For query-time, use ONNX-optimized model (~10ms per query on CPU).
- Execute all three searches concurrently via `asyncio.gather()` in the FastAPI endpoint.
- Implement configurable fusion weights in environment variables for rapid A/B testing without code changes.

## References

- [OpenAI text-embedding-3-large](https://platform.openai.com/docs/guides/embeddings)
- [PubMedBERT (Microsoft)](https://huggingface.co/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext)
- [BLURB Biomedical NLP Benchmark](https://microsoft.github.io/BLURB/)
- [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [Qdrant Named Vectors](https://qdrant.tech/documentation/concepts/vectors/#named-vectors)
- ADR-001: Vector Database Selection (Qdrant)
- ADR-002: Chunking Strategy
