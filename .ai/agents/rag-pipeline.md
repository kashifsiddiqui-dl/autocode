# RAG/ML Pipeline Agent

## Role

RAG (Retrieval-Augmented Generation) and ML pipeline agent responsible for the core intelligence layer of Auto Code -- parsing ICD-10-CM source data, generating embeddings, managing the vector store, performing hybrid retrieval, reranking results, and orchestrating LLM-based code assignment with strict guardrails.

## Scope

All files within the following directories:

- `backend/app/rag/` -- Retrieval, reranking, prompting, and LLM integration
- `backend/app/ingestion/` -- XML parsing, chunking, embedding generation, Qdrant loading
- `scripts/` -- Data pipeline scripts (ingest, benchmark, evaluate)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Vector Database | Qdrant (self-hosted, Docker) |
| Embeddings | OpenAI `text-embedding-3-large` (primary), sentence-transformers (fallback/comparison) |
| LLM - Primary | Anthropic Claude (via Anthropic SDK) |
| LLM - Secondary | OpenAI GPT-4o (via OpenAI SDK) |
| XML Parsing | lxml (high-performance XML processing) |
| Reranking | Cross-encoder models (sentence-transformers) |
| Language | Python 3.12+ |
| Data Format | ICD-10-CM April 2026 XML release (5 files) |

## Responsibilities

### XML Parsing (5 ICD-10-CM Source Files)

Parse the official CMS ICD-10-CM April 2026 XML release files located in `data/ICD-10-CM/icd10cm-April-1-2026-XML/`:

1. **`icd10c-tabular-April-1-2026.xml`** -- The primary tabular list. Contains all ICD-10-CM codes organized by chapter > section > category > subcategory. Includes code descriptions, includes/excludes notes (Excludes1, Excludes2), code-first/use-additional instructions, and 7th character definitions. This is the most critical file.

2. **`icd10cm-index-April-1-2026-XML.xml`** -- Alphabetic index. Maps clinical terms, conditions, and diagnoses to ICD-10-CM codes. Contains main terms, subterms, and see/see-also cross-references.

3. **`icd10cm-eindex-April-1-2026-XML.xml`** -- External cause index. Maps external causes of injury (accidents, falls, assaults) to codes in the V00-Y99 range.

4. **`icd10cm-drug-April-1-2026-XML.xml`** -- Table of drugs and chemicals. Maps substances to poisoning, adverse effect, and underdosing codes with intent columns (accidental, intentional, assault, undetermined).

5. **`icd10cm-neoplasm-April-1-2026-XML.xml`** -- Neoplasm table. Maps anatomical sites to neoplasm codes with behavior columns (malignant primary, malignant secondary, in situ, benign, uncertain, unspecified).

### Code-Centric Chunking Strategy

The chunking strategy is **code-centric**, not passage-centric. Each chunk represents a single ICD-10-CM code with its full context:

- **Chunk = One Code**: Each ICD-10-CM code becomes one chunk/document in Qdrant.
- **Rich Context Per Chunk**: Each chunk includes:
  - Code (e.g., `S72.001A`)
  - Short description
  - Long description
  - Full hierarchy path (Chapter > Section > Category > Code)
  - Includes notes
  - Excludes1 notes (codes that can NEVER be used together)
  - Excludes2 notes (codes that CAN be used together if both conditions exist)
  - Code-first / Use-additional instructions
  - 7th character extensions and their meanings
  - Index entries that point to this code (from alphabetic index)
  - Neoplasm table entries (if applicable)
  - Drug table entries (if applicable)
- **Parent Context Inheritance**: Category-level notes (includes, excludes, instructions) are inherited by all child codes. A code at `S72.001A` includes notes from `S72`, `S72.0`, and `S72.00`.
- **Cross-Reference Linking**: See/see-also references from the index are resolved and included as metadata.

### Embedding Generation

- Generate vector embeddings for each code chunk.
- **Embedding Input**: Concatenation of code + short description + long description + key index terms. Not the full chunk -- the full chunk is stored as payload, but the embedding is generated from the most semantically meaningful fields.
- **Model**: OpenAI `text-embedding-3-large` (3072 dimensions) as primary. Benchmark against `text-embedding-3-small` and sentence-transformers models for cost/quality tradeoff.
- **Batch Processing**: Embed in batches of 100-500 to respect rate limits and optimize throughput.
- **Idempotent Loading**: Re-running the pipeline replaces existing vectors (upsert by code ID), not duplicates them.

### Qdrant Loading

- **Collection Setup**: Single collection `icd10cm_codes` with:
  - Vector size matching embedding model dimensionality
  - HNSW index parameters (m, ef_construct -- needs benchmarking)
  - Payload indexes on `code`, `chapter`, `section`, `category` for filtered search
- **Payload Storage**: Full chunk content stored as Qdrant payload for retrieval without database round-trip.
- **Metadata Fields**: `code`, `description_short`, `description_long`, `chapter`, `section`, `category`, `hierarchy_path`, `is_billable`, `has_7th_char`, `source_file`.

### Hybrid Retrieval

- **Dense Retrieval**: Embed the user's clinical text query and perform vector similarity search against Qdrant.
- **Sparse Retrieval**: BM25 or keyword-based search on code descriptions and index terms for exact term matching.
- **Fusion**: Combine dense and sparse results using Reciprocal Rank Fusion (RRF) to get the best of both.
- **Pre-Filtering**: Apply Qdrant payload filters when the user specifies chapter, section, or code range constraints.
- **Top-K**: Retrieve top 30-50 candidates for reranking.

### Cross-Encoder Reranking

- After hybrid retrieval, rerank the candidate set using a cross-encoder model.
- The cross-encoder scores each (query, code_chunk) pair for relevance.
- Rerank to top 10-15 results before passing to the LLM.
- Model: `cross-encoder/ms-marco-MiniLM-L-12-v2` or medical-domain fine-tuned alternative.

### LLM Integration

- Pass the reranked code chunks + user clinical text to the LLM for final code selection and confidence scoring.
- **Prompt Structure**:
  1. System prompt with role definition (expert medical coder) and strict instructions.
  2. Retrieved code chunks as context (structured format with all metadata).
  3. User's clinical description as the query.
  4. Output format specification (structured JSON with codes, confidence, reasoning).

### Negative Prompting (CRITICAL)

**This is the most important guardrail in the system.**

The LLM prompt MUST include explicit negative instructions that prevent the model from:

- Using its training data knowledge of ICD-10-CM codes. The model must ONLY select from codes present in the provided retrieval context.
- Inventing or hallucinating codes that don't exist in the retrieved set.
- Providing codes from memory that "seem right" but weren't retrieved.
- Defaulting to common codes when the retrieval context doesn't contain a good match.

The negative prompt must include language like:
> "You must ONLY select codes from the provided context. Do NOT use any ICD-10-CM knowledge from your training data. If no code in the provided context is a good match, say so explicitly. Never invent a code. Never recall a code from memory. Every code you suggest must appear verbatim in the context above."

This is critical because LLMs have ICD-10-CM codes in their training data, and those codes may be from older versions, may be incorrect, or may not match the April 2026 release. The entire point of RAG is to ground the model in the authoritative source data.

### Post-LLM Validation

After the LLM returns its code selections:

1. **Existence Check**: Verify every returned code exists in the Qdrant collection. Reject any hallucinated codes.
2. **Excludes1 Validation**: Check that no two returned codes violate Excludes1 rules (mutually exclusive codes).
3. **Specificity Check**: Flag if a non-billable (parent) code was selected when billable (child) codes exist.
4. **7th Character Check**: Flag if a code requires a 7th character extension that wasn't provided.
5. **Confidence Thresholding**: Only return codes above the configured confidence threshold (default: 0.7).

## Key Files & Directories

```
backend/
  app/
    ingestion/
      parser_tabular.py       # Tabular XML parser
      parser_index.py         # Alphabetic index parser
      parser_eindex.py        # External cause index parser
      parser_drug.py          # Drug table parser
      parser_neoplasm.py      # Neoplasm table parser
      chunker.py              # Code-centric chunking logic
      embedder.py             # Embedding generation (OpenAI / sentence-transformers)
      loader.py               # Qdrant collection setup and vector upsert
      pipeline.py             # End-to-end ingestion orchestrator
    rag/
      retriever.py            # Hybrid retrieval (dense + sparse + fusion)
      reranker.py             # Cross-encoder reranking
      prompts.py              # LLM prompt templates (system, user, negative)
      llm_client.py           # Anthropic + OpenAI SDK wrappers
      validator.py            # Post-LLM validation (existence, excludes, specificity)
      pipeline.py             # End-to-end RAG orchestrator
      config.py               # RAG-specific configuration (top-k, thresholds, model names)
  scripts/
    ingest.py                 # CLI script to run full ingestion pipeline
    benchmark.py              # RAG quality benchmarking against test cases
    evaluate.py               # Evaluation metrics (precision, recall, MRR, nDCG)
    inspect_collection.py     # Utility to inspect Qdrant collection contents

data/
  ICD-10-CM/
    icd10cm-April-1-2026-XML/   # Source XML files (gitignored, large)
```

## Dependencies

- **ICD-10-CM Data Files**: The 5 XML files in `data/ICD-10-CM/icd10cm-April-1-2026-XML/`. These are the authoritative source. Must be present locally for ingestion.
- **Qdrant**: Vector database. Runs as a Docker container in dev (`localhost:6333`), dedicated instance in production.
- **OpenAI API**: For embedding generation and optional GPT-4o LLM calls. Requires `OPENAI_API_KEY`.
- **Anthropic API**: For Claude LLM calls. Requires `ANTHROPIC_API_KEY`.
- **Backend API**: The RAG pipeline is invoked by the backend coding service. It is a Python module imported directly, not a separate service.
- **PostgreSQL**: The ICD10Code reference table (denormalized from parsed XML) is used for post-LLM validation and browse functionality.

## Guidelines

### Data Pipeline Principles

1. **Idempotent**: The ingestion pipeline can be run repeatedly without creating duplicates. Use upsert operations keyed on the ICD-10-CM code.
2. **Reproducible**: Given the same input XML files and configuration, the pipeline produces identical output. Pin model versions, fix random seeds where applicable.
3. **Observable**: Log progress at every stage (parsing, chunking, embedding, loading) with counts and timing. Surface errors without halting the entire pipeline -- collect and report at the end.
4. **Incremental (Future)**: Design for future support of incremental updates when CMS releases addenda or new versions.

### Retrieval Quality

- Maintain a benchmark test set of clinical descriptions with expected ICD-10-CM codes (ground truth from certified coders).
- Track retrieval metrics: Precision@K, Recall@K, MRR (Mean Reciprocal Rank), nDCG.
- Any change to parsing, chunking, embedding, or retrieval logic must be evaluated against the benchmark before merging.
- Target: >90% Recall@10 on the benchmark set.

### LLM Integration Rules

1. **Context Window Budget**: Track token usage. The retrieved context + prompt must fit within the model's context window with room for the response. Truncate lower-ranked chunks if necessary.
2. **Structured Output**: Always request structured JSON output from the LLM. Use Pydantic models to validate the LLM response.
3. **Retry with Fallback**: If the primary LLM (Claude) fails or times out, fall back to the secondary (GPT-4o). Log all fallback events.
4. **Cost Tracking**: Log token usage and estimated cost per request. Surface in admin analytics.
5. **Temperature**: Use temperature 0 for coding tasks. Deterministic output is essential for medical coding.

### Negative Prompting is Non-Negotiable

- Every code review of prompt changes MUST verify that negative prompting language is preserved and strengthened, never weakened.
- Test cases must include adversarial scenarios where the correct code is NOT in the retrieval context, to verify the model refuses to hallucinate.
- The negative prompt is not just a suggestion -- it is a patient safety measure. Incorrect codes lead to incorrect billing and potentially incorrect treatment decisions.

### Security & Compliance

- Clinical text (PHI) must never be logged in full. Log only anonymized metadata (query length, number of results, processing time).
- API keys for OpenAI and Anthropic must come from environment variables, never hardcoded.
- The ingestion pipeline does not handle PHI -- ICD-10-CM codes are public reference data. But the retrieval pipeline processes user-submitted clinical text, which may contain PHI.
