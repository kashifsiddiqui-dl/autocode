# Auto Code - Data Flow Documentation

This document details the data flows through the Auto Code system, covering ingestion, coding requests, exports, and audit logging.

---

## 1. ICD-10-CM Data Ingestion Flow

The data ingestion pipeline transforms raw CMS ICD-10-CM release files into searchable vector embeddings and structured relational data. This is a batch process triggered when a new ICD-10-CM release is published (typically annually on October 1, with mid-year updates on April 1).

### 1.1 Source Data

The April 1, 2026 release includes the following source files:

| File | Format | Content |
|---|---|---|
| `icd10c-tabular-April-1-2026.xml` | XML | Full tabular list: chapters, sections, categories, codes with descriptions, includes, excludes, notes |
| `icd10cm-index-April-1-2026-XML.xml` | XML | Alphabetic Index to Diseases and Injuries |
| `icd10cm-eindex-April-1-2026-XML.xml` | XML | External Causes of Injuries Index |
| `icd10cm-drug-April-1-2026-XML.xml` | XML | Table of Drugs and Chemicals |
| `icd10cm-neoplasm-April-1-2026-XML.xml` | XML | Neoplasm Table |
| `ICD-10-CM April 1 2026 Guidelines Final.pdf` | PDF | Official Coding Guidelines |
| `icd10cm-codes-April-1-2026.txt` | TXT | Flat list of all valid codes |
| `icd10cm-order-April-1-2026.txt` | TXT | Code order file with long/short descriptions |
| `icd10cm-codes-addenda-April-1-2026.txt` | TXT | Changes from previous release |

### 1.2 Ingestion Pipeline

```
 PHASE 1: EXTRACTION
 ====================

 +------------------+       +-------------------+       +------------------+
 | Tabular XML      |------>| TabularParser     |------>| Structured Code  |
 | (icd10c-tabular) |       | (lxml.etree)      |       | Records          |
 +------------------+       |                   |       |                  |
                            | Extracts:         |       | Fields:          |
                            | - Chapter/section |       | - code           |
                            | - Category/code   |       | - description    |
                            | - Descriptions    |       | - long_desc      |
                            | - Includes notes  |       | - chapter        |
                            | - Excludes1 notes |       | - section        |
                            | - Excludes2 notes |       | - category       |
                            | - Code First      |       | - parent_code    |
                            | - Use Additional  |       | - includes       |
                            | - 7th char defs   |       | - excludes1[]    |
                            +-------------------+       | - excludes2[]    |
                                                        | - use_additional |
                                                        | - code_first     |
                                                        | - is_billable    |
                                                        | - hierarchy_level|
                                                        +------------------+

 +------------------+       +-------------------+       +------------------+
 | Index XML        |------>| IndexParser       |------>| Index Entry      |
 | (icd10cm-index)  |       |                   |       | Records          |
 +------------------+       | Extracts:         |       |                  |
                            | - Main terms      |       | Fields:          |
 +------------------+       | - Subterms        |       | - main_term      |
 | EIndex XML       |------>| - See/see also    |       | - subterms[]     |
 | (icd10cm-eindex) |       | - Code references |       | - code_refs[]    |
 +------------------+       | - Neoplasm refs   |       | - see_also[]     |
                            +-------------------+       | - source (index/ |
                                                        |   eindex)        |
                                                        +------------------+

 +------------------+       +-------------------+       +------------------+
 | Drug XML         |------>| DrugTableParser   |------>| Drug Table       |
 | (icd10cm-drug)   |       |                   |       | Records          |
 +------------------+       | Extracts:         |       |                  |
                            | - Substance name  |       | Fields:          |
                            | - Poisoning codes |       | - substance      |
                            |   (accidental,    |       | - poisoning_     |
                            |    intentional,   |       |   accidental     |
                            |    assault,       |       | - poisoning_     |
                            |    undetermined)  |       |   intentional    |
                            | - Adverse effect  |       | - poisoning_     |
                            | - Underdosing     |       |   assault        |
                            +-------------------+       | - adverse_effect |
                                                        | - underdosing    |
                                                        +------------------+

 +------------------+       +-------------------+       +------------------+
 | Neoplasm XML     |------>| NeoplasmParser    |------>| Neoplasm Table   |
 | (icd10cm-neoplasm|       |                   |       | Records          |
 +------------------+       | Extracts:         |       |                  |
                            | - Anatomical site |       | Fields:          |
                            | - Malignant       |       | - site           |
                            |   primary/second  |       | - malignant_     |
                            | - Ca in situ      |       |   primary        |
                            | - Benign          |       | - malignant_     |
                            | - Uncertain       |       |   secondary      |
                            | - Unspecified     |       | - ca_in_situ     |
                            +-------------------+       | - benign         |
                                                        | - uncertain      |
                                                        | - unspecified    |
                                                        +------------------+

 +------------------+       +-------------------+       +------------------+
 | Guidelines PDF   |------>| GuidelineParser   |------>| Guideline        |
 |                  |       | (PDF extraction)  |       | Sections         |
 +------------------+       |                   |       |                  |
                            | Extracts:         |       | Fields:          |
                            | - Section headers |       | - section_id     |
                            | - Convention text |       | - title          |
                            | - Chapter-specific|       | - content        |
                            |   guidelines      |       | - chapter_ref    |
                            | - General rules   |       | - applicable_    |
                            +-------------------+       |   categories[]   |
                                                        +------------------+


 PHASE 2: CHUNKING
 ==================

 All parsed records flow into the Chunking Engine, which produces 4 chunk types:

 +-------------------------------------------------------------------+
 |                        Chunking Engine                             |
 |                                                                   |
 |  Input: Parsed records from all 5 parsers                         |
 |  Output: ~130,000 chunks                                          |
 |                                                                   |
 |  +-------------------------------------------------------------+ |
 |  | Chunk Type 1: CODE CONTEXT (~72,000 chunks)                 | |
 |  |                                                             | |
 |  | One chunk per billable code. Combines:                      | |
 |  | - Code + short description + long description               | |
 |  | - Parent category description                               | |
 |  | - Inclusion notes                                           | |
 |  | - Excludes1 and Excludes2 notes                             | |
 |  | - "Code first" / "Use additional code" instructions         | |
 |  | - 7th character definitions (if applicable)                 | |
 |  | - Relevant guideline snippets                               | |
 |  |                                                             | |
 |  | Rationale: Groups everything a coder needs for one code     | |
 |  +-------------------------------------------------------------+ |
 |                                                                   |
 |  +-------------------------------------------------------------+ |
 |  | Chunk Type 2: INDEX ENTRY (~45,000 chunks)                  | |
 |  |                                                             | |
 |  | One chunk per main term + subterm path. Combines:           | |
 |  | - Main term                                                 | |
 |  | - Subterm hierarchy (indented path)                         | |
 |  | - Referenced codes                                          | |
 |  | - See / see also references                                 | |
 |  |                                                             | |
 |  | Rationale: Mirrors how coders look up codes by condition    | |
 |  +-------------------------------------------------------------+ |
 |                                                                   |
 |  +-------------------------------------------------------------+ |
 |  | Chunk Type 3: DRUG TABLE ENTRY (~6,000 chunks)              | |
 |  |                                                             | |
 |  | One chunk per substance. Combines:                          | |
 |  | - Substance name                                            | |
 |  | - All poisoning codes by intent                             | |
 |  | - Adverse effect code                                       | |
 |  | - Underdosing code                                          | |
 |  |                                                             | |
 |  | Rationale: Drug/chemical lookups are a distinct workflow     | |
 |  +-------------------------------------------------------------+ |
 |                                                                   |
 |  +-------------------------------------------------------------+ |
 |  | Chunk Type 4: NEOPLASM TABLE ENTRY (~8,000 chunks)          | |
 |  |                                                             | |
 |  | One chunk per anatomical site. Combines:                    | |
 |  | - Anatomical site (with hierarchy)                          | |
 |  | - Malignant primary/secondary codes                         | |
 |  | - Ca in situ, benign, uncertain, unspecified codes          | |
 |  |                                                             | |
 |  | Rationale: Neoplasm coding requires the table for accuracy  | |
 |  +-------------------------------------------------------------+ |
 +-------------------------------------------------------------------+


 PHASE 3: EMBEDDING
 ====================

 +------------------+       +-------------------+       +------------------+
 | Chunks           |------>| Embedding Service |------>| Embedded Chunks  |
 | (~130K)          |       |                   |       |                  |
 +------------------+       | For each chunk:   |       | Each chunk has:  |
                            |                   |       |                  |
                            | 1. Generate       |       | - description_vec|
                            |    description    |       |   (3072-dim,     |
                            |    vector via     |       |    float32)      |
                            |    text-embedding-|       |                  |
                            |    3-large        |       | - clinical_vec   |
                            |    (3072 dims)    |       |   (768-dim,      |
                            |                   |       |    float32)      |
                            | 2. Generate       |       |                  |
                            |    clinical       |       | - sparse_vec     |
                            |    context vector |       |   (BM25 indices  |
                            |    via PubMedBERT |       |    + values)     |
                            |    (768 dims)     |       |                  |
                            |                   |       | - payload        |
                            | 3. Generate BM25  |       |   metadata       |
                            |    sparse vector  |       |                  |
                            +-------------------+       +------------------+

 Batching: 100 chunks per embedding API call
 Rate limiting: Respect OpenAI rate limits (3,000 RPM for text-embedding-3-large)
 Estimated time: ~45 minutes for full 130K chunk embedding


 PHASE 4: LOADING
 ==================

 +------------------+                      +------------------------+
 | Embedded Chunks  |----(upsert)--------->| Qdrant Collection      |
 |                  |                      | "icd10cm_codes"        |
 +------------------+                      |                        |
                                           | - Named vectors:       |
                                           |   "description" (3072) |
                                           |   "clinical" (768)     |
                                           | - Sparse vectors:      |
                                           |   "bm25"               |
                                           | - Payload:             |
                                           |   code, chunk_type,    |
                                           |   category, chapter,   |
                                           |   version_year,        |
                                           |   hierarchy_level,     |
                                           |   parent_code,         |
                                           |   description_text     |
                                           +------------------------+

 +------------------+                      +------------------------+
 | Parsed Records   |----(INSERT/UPDATE)-->| PostgreSQL Tables      |
 |                  |                      |                        |
 +------------------+                      | icd10cm_codes:         |
                                           |   code, description,   |
                                           |   long_description,    |
                                           |   is_billable, chapter,|
                                           |   section, category,   |
                                           |   parent_code,         |
                                           |   hierarchy_level,     |
                                           |   includes, excludes1, |
                                           |   excludes2,           |
                                           |   use_additional,      |
                                           |   code_first,          |
                                           |   seventh_char_defs,   |
                                           |   version_year,        |
                                           |   is_active            |
                                           |                        |
                                           | icd10cm_categories:    |
                                           |   category, chapter,   |
                                           |   section, description,|
                                           |   parent_category      |
                                           |                        |
                                           | icd10cm_guidelines:    |
                                           |   section_id, title,   |
                                           |   content, chapter_ref,|
                                           |   applicable_categories|
                                           |                        |
                                           | icd10cm_drug_table:    |
                                           |   substance, codes...  |
                                           |                        |
                                           | icd10cm_neoplasm_table:|
                                           |   site, codes...       |
                                           +------------------------+


 PHASE 5: VALIDATION
 =====================

 +-------------------------------------------------------------------+
 | Post-Load Validation                                              |
 |                                                                   |
 | 1. Code count check                                               |
 |    - Compare Qdrant point count vs icd10cm-codes.txt line count   |
 |    - Expected: ~72,000+ billable codes, ~130K total chunks        |
 |                                                                   |
 | 2. Sample search validation                                       |
 |    - Run 50 known clinical queries                                |
 |    - Verify expected codes appear in top-10 results               |
 |    - Log precision/recall metrics                                 |
 |                                                                   |
 | 3. Hierarchy integrity                                            |
 |    - Every code has a valid parent_code (except chapter headers)  |
 |    - Every category maps to a valid chapter                       |
 |    - No orphaned codes                                            |
 |                                                                   |
 | 4. Excludes cross-reference check                                 |
 |    - All codes referenced in Excludes1/2 notes exist in master    |
 |                                                                   |
 | 5. Version activation                                             |
 |    - Mark new version as "active"                                 |
 |    - Mark previous version as "archived" (not deleted)            |
 |    - Update default version_year in tenant settings               |
 +-------------------------------------------------------------------+
```

### 1.3 Addenda Processing

When CMS publishes addenda (code additions, revisions, deletions):

1. Parse addenda files (`icd10cm-codes-addenda-April-1-2026.txt` and addenda PDFs)
2. Identify changes: new codes, revised descriptions, deleted codes
3. For new codes: run full chunk-embed-load pipeline for the new codes only
4. For revised codes: update chunk content, re-embed, upsert to Qdrant and PostgreSQL
5. For deleted codes: soft-delete in PostgreSQL (set `is_active = false`), remove from Qdrant
6. Re-run validation suite

---

## 2. Coding Request Flow

This is the primary runtime data flow. A medical coder submits clinical documentation and receives ICD-10-CM code suggestions.

### 2.1 Request Path

```
 +---------------------------------------------------------------------+
 | CLIENT                                                              |
 |                                                                     |
 | POST /api/v1/coding/suggest                                         |
 | Headers:                                                            |
 |   Cookie: access_token=<JWT>                                        |
 |   Content-Type: application/json                                    |
 |                                                                     |
 | Body:                                                               |
 | {                                                                   |
 |   "clinical_text": "Patient presents with acute exacerbation of     |
 |     moderate persistent asthma with status asthmaticus. History      |
 |     of allergic rhinitis. Current medications include fluticasone    |
 |     and albuterol.",                                                |
 |   "encounter_type": "inpatient",                                    |
 |   "coding_context": {                                               |
 |     "patient_age": 34,                                              |
 |     "patient_sex": "F"                                              |
 |   },                                                                |
 |   "preferences": {                                                  |
 |     "max_suggestions": 10,                                          |
 |     "include_reasoning": true,                                      |
 |     "version_year": "2026"                                          |
 |   }                                                                 |
 | }                                                                   |
 +-----------------------------------+---------------------------------+
                                     |
                                     v
 +-----------------------------------+---------------------------------+
 | NGINX API GATEWAY                                                   |
 |                                                                     |
 | 1. Rate limit check (100 req/min per user)                          |
 | 2. Request size validation (<1MB)                                   |
 | 3. Forward to upstream FastAPI                                      |
 +-----------------------------------+---------------------------------+
                                     |
                                     v
 +-----------------------------------+---------------------------------+
 | FASTAPI MIDDLEWARE CHAIN                                            |
 |                                                                     |
 | 1. CORSMiddleware - validate origin                                 |
 | 2. AuthenticationMiddleware:                                        |
 |    a. Extract JWT from httpOnly cookie                              |
 |    b. Validate signature (RS256, public key from JWKS)              |
 |    c. Check expiration                                              |
 |    d. Extract claims: user_id, tenant_id, roles                     |
 |    e. Attach to request.state                                       |
 | 3. TenantContextMiddleware:                                         |
 |    a. Get tenant_id from JWT claims                                 |
 |    b. Set PostgreSQL session variable:                              |
 |       SET app.current_tenant = '<tenant_id>'                        |
 |    c. RLS now active for all queries in this request                |
 | 4. RequestLoggingMiddleware:                                        |
 |    a. Generate request_id (UUID)                                    |
 |    b. Log: timestamp, user_id, tenant_id, endpoint, IP, user_agent |
 +-----------------------------------+---------------------------------+
                                     |
                                     v
 +-----------------------------------+---------------------------------+
 | FASTAPI ENDPOINT: coding_router.suggest()                           |
 |                                                                     |
 | 1. Pydantic validation of request body (CodingSuggestRequest)       |
 | 2. Authorization check: user has "code:write" permission            |
 | 3. Input sanitization:                                              |
 |    a. Strip HTML/script tags                                        |
 |    b. Normalize whitespace                                          |
 |    c. Truncate to max 10,000 characters                             |
 | 4. Create CodingSession record in PostgreSQL                        |
 |    (session_id, user_id, tenant_id, timestamp, status="processing") |
 | 5. Invoke RAG pipeline                                              |
 +-----------------------------------+---------------------------------+
                                     |
                                     v
 +---------------------------------------------------------------------+
 | RAG PIPELINE                                                        |
 |                                                                     |
 | STAGE 1: HYBRID SEARCH (Qdrant)                                     |
 | ================================                                    |
 |                                                                     |
 |  a. Embed clinical_text with text-embedding-3-large -> desc_vec     |
 |  b. Embed clinical_text with PubMedBERT -> clinical_vec             |
 |  c. Tokenize clinical_text for BM25 sparse vector -> sparse_vec    |
 |                                                                     |
 |  d. Execute 3 parallel Qdrant searches:                             |
 |     - Dense search on "description" named vector (top-100)          |
 |     - Dense search on "clinical" named vector (top-100)             |
 |     - Sparse search on "bm25" sparse vector (top-100)              |
 |                                                                     |
 |  e. Reciprocal Rank Fusion (RRF):                                   |
 |     score(doc) = SUM(1 / (k + rank_i)) for each result list         |
 |     k = 60 (standard RRF constant)                                  |
 |     Merge 3 result lists into single ranked list                    |
 |     Output: top-100 candidate chunks                                |
 |                                                                     |
 | STAGE 2: METADATA FILTERING                                         |
 | =============================                                       |
 |                                                                     |
 |  a. Filter by version_year = requested version (e.g., "2026")       |
 |  b. If encounter_type provided, boost relevant chunk_types:          |
 |     - "inpatient" -> boost code_context chunks with 7th char defs   |
 |     - "outpatient" -> no special boost                              |
 |  c. Lightweight NER on clinical_text to extract category hints:     |
 |     - Detect anatomical terms -> filter to relevant chapters        |
 |     - Detect drug mentions -> include drug_table chunks             |
 |     - Detect neoplasm terms -> include neoplasm_table chunks        |
 |  d. Score adjustment based on chunk_type relevance                  |
 |  e. Output: top-60 candidate chunks                                |
 |                                                                     |
 | STAGE 3: CROSS-ENCODER RERANKING                                    |
 | ==================================                                  |
 |                                                                     |
 |  a. For each of 60 candidate chunks:                                |
 |     - Concatenate: [clinical_text] [SEP] [chunk_text]               |
 |     - Score with ms-marco-MiniLM-L-12 cross-encoder                |
 |     - Produces relevance score [0, 1]                               |
 |  b. Sort by cross-encoder score descending                          |
 |  c. Output: top-20 chunks                                           |
 |                                                                     |
 | STAGE 4: HIERARCHY EXPANSION (PostgreSQL)                           |
 | ==========================================                          |
 |                                                                     |
 |  For each unique code in top-20 chunks:                             |
 |                                                                     |
 |  a. Fetch from icd10cm_codes:                                       |
 |     - Parent category description                                   |
 |     - Section and chapter descriptions                              |
 |     - Includes notes for the category                               |
 |     - Excludes1 list (cannot be coded together)                     |
 |     - Excludes2 list (not included here, code separately)           |
 |     - "Code first" underlying condition instructions               |
 |     - "Use additional code" instructions                            |
 |     - 7th character extension definitions                           |
 |                                                                     |
 |  b. Fetch sibling codes under same category:                        |
 |     - Provides context for specificity decisions                    |
 |                                                                     |
 |  c. Fetch relevant guideline sections from icd10cm_guidelines:      |
 |     - Chapter-specific guidelines                                   |
 |     - General coding conventions (Section I.A)                      |
 |     - Selection of principal diagnosis (Section II)                 |
 |                                                                     |
 |  d. Build context package:                                          |
 |     - top-20 chunks with hierarchy context                          |
 |     - Coding guidelines snippets                                    |
 |     - Excludes cross-references                                     |
 |                                                                     |
 |  Output: Enriched context package for LLM                           |
 +-----------------------------------+---------------------------------+
                                     |
                                     v
 +-----------------------------------+---------------------------------+
 | LLM REASONING                                                       |
 |                                                                     |
 | Model: Claude Sonnet (primary) or GPT-4o (fallback)                 |
 |                                                                     |
 | System prompt (see rag-pipeline.md for full template):              |
 | - Role definition: expert ICD-10-CM medical coder                   |
 | - Retrieved context: top-20 enriched chunks                         |
 | - Negative prompting instructions (what NOT to code)                |
 | - Output format specification (structured JSON)                     |
 | - Confidence scoring rubric                                         |
 |                                                                     |
 | User message: clinical_text + encounter_type + patient context      |
 |                                                                     |
 | Expected output:                                                    |
 | {                                                                   |
 |   "primary_diagnosis": {                                            |
 |     "code": "J45.41",                                               |
 |     "description": "Moderate persistent asthma with acute           |
 |       exacerbation",                                                |
 |     "confidence": 0.92,                                             |
 |     "reasoning": "Clinical text explicitly states..."               |
 |   },                                                                |
 |   "additional_diagnoses": [                                         |
 |     {                                                               |
 |       "code": "J45.42",                                             |
 |       "description": "Moderate persistent asthma with status        |
 |         asthmaticus",                                               |
 |       "confidence": 0.95,                                           |
 |       "reasoning": "Status asthmaticus is explicitly documented..." |
 |     },                                                              |
 |     {                                                               |
 |       "code": "J30.9",                                              |
 |       "description": "Allergic rhinitis, unspecified",              |
 |       "confidence": 0.88,                                           |
 |       "reasoning": "History of allergic rhinitis documented..."     |
 |     }                                                               |
 |   ],                                                                |
 |   "coding_notes": [                                                 |
 |     "J45.41 and J45.42 are mutually exclusive. J45.42 (status       |
 |      asthmaticus) is the more specific condition documented.",       |
 |     "Consider sequencing: status asthmaticus as principal diagnosis  |
 |      for inpatient encounter per Section II guidelines."            |
 |   ],                                                                |
 |   "requires_review": false                                          |
 | }                                                                   |
 +-----------------------------------+---------------------------------+
                                     |
                                     v
 +-----------------------------------+---------------------------------+
 | POST-LLM VALIDATION                                                 |
 |                                                                     |
 | 1. Code existence check:                                            |
 |    - Query icd10cm_codes for each suggested code                    |
 |    - Reject any code not in the active version                      |
 |                                                                     |
 | 2. Billable code check:                                             |
 |    - Verify each code is_billable = true                            |
 |    - If LLM suggested a category code, flag it and suggest          |
 |      more specific codes under that category                        |
 |                                                                     |
 | 3. Excludes1 conflict detection:                                    |
 |    - Check all pairs of suggested codes against Excludes1 lists     |
 |    - If conflict found, flag with warning message                   |
 |                                                                     |
 | 4. Specificity validation:                                          |
 |    - If code requires 7th character and it is missing, flag         |
 |    - If laterality is required and not specified, flag              |
 |    - If placeholder 'x' is needed, verify correct format            |
 |                                                                     |
 | 5. "Use additional code" check:                                     |
 |    - If a suggested code has "use additional code" note,            |
 |      verify the additional code is also suggested or flagged        |
 |                                                                     |
 | 6. "Code first" check:                                              |
 |    - If a suggested code has "code first" instruction,              |
 |      verify the underlying condition code is present or flagged     |
 |                                                                     |
 | 7. Confidence recalibration:                                        |
 |    - Adjust confidence scores based on validation results           |
 |    - Codes with warnings get reduced confidence                     |
 |    - Codes passing all checks may get slight confidence boost       |
 +-----------------------------------+---------------------------------+
                                     |
                                     v
 +-----------------------------------+---------------------------------+
 | RESPONSE ASSEMBLY                                                   |
 |                                                                     |
 | 1. Build CodingSuggestResponse:                                     |
 |    - Validated code suggestions with confidence and reasoning        |
 |    - Validation warnings and notes                                  |
 |    - Coding guidelines references                                   |
 |    - Processing metadata (model used, latency, retrieval stats)     |
 |                                                                     |
 | 2. Persist to PostgreSQL:                                           |
 |    - Update CodingSession: status="completed", response data        |
 |    - Insert CodingResult records for each suggestion                |
 |    - Update session metrics: latency, chunk_count, model            |
 |                                                                     |
 | 3. Audit log entry:                                                 |
 |    - action: "coding_suggest"                                       |
 |    - user_id, tenant_id, session_id                                 |
 |    - codes_suggested: ["J45.42", "J30.9"]                           |
 |    - model_used: "claude-sonnet-4-20250514"                         |
 |    - latency_ms: 3200                                               |
 |    - ip_address, user_agent                                         |
 |                                                                     |
 | 4. Return HTTP 200 with JSON response                               |
 +---------------------------------------------------------------------+
```

### 2.2 Code Acceptance Flow

After the coder reviews suggestions, they accept or reject each code:

```
 POST /api/v1/coding/sessions/{session_id}/accept
 {
   "accepted_codes": ["J45.42", "J30.9"],
   "rejected_codes": ["J45.41"],
   "rejection_reasons": {
     "J45.41": "J45.42 is more specific - status asthmaticus documented"
   },
   "manual_codes": [],
   "notes": "Status asthmaticus confirmed per physician documentation"
 }

      |
      v

 +-------------------------------------------------------------------+
 | 1. Update CodingResult records:                                   |
 |    - accepted_codes: status = "accepted"                          |
 |    - rejected_codes: status = "rejected", reason stored           |
 |    - manual_codes: status = "manual_add" (coder added manually)   |
 |                                                                   |
 | 2. Audit log:                                                     |
 |    - action: "coding_accept"                                      |
 |    - accepted/rejected/manual code lists                          |
 |    - user_id, session_id, timestamp                               |
 |                                                                   |
 | 3. Feedback loop (future):                                        |
 |    - Accepted/rejected signals feed into retrieval tuning         |
 |    - Track accuracy metrics per code category                     |
 +-------------------------------------------------------------------+
```

### 2.3 Error Handling

| Error Scenario | HTTP Status | Handling |
|---|---|---|
| Invalid/expired JWT | 401 | Return error, client redirects to login |
| Insufficient permissions | 403 | Return error with required permission |
| Rate limit exceeded | 429 | Return Retry-After header |
| Input validation failure | 422 | Return Pydantic validation errors |
| Qdrant unavailable | 503 | Return error, log alert, trigger CloudWatch alarm |
| LLM API timeout (>30s) | 504 | Retry once with fallback model, then return partial results |
| LLM returns invalid JSON | 500 | Retry with stricter prompt, log for review |
| All codes fail validation | 200 | Return empty suggestions with explanation, flag for human review |

### 2.4 Latency Budget

| Stage | Target P95 | Notes |
|---|---|---|
| Embedding generation | 200ms | 2 parallel API calls (description + clinical) |
| Hybrid search (Qdrant) | 80ms | 3 parallel searches, RRF merge |
| Metadata filtering | 10ms | In-memory filtering |
| Cross-encoder reranking | 300ms | 60 pairs, batched inference |
| Hierarchy expansion (PG) | 50ms | Batch query with IN clause |
| LLM reasoning | 3,000ms | Primary latency bottleneck |
| Post-validation | 30ms | Batch queries |
| Response assembly | 10ms | Serialization |
| **Total** | **~3,700ms** | Target: <5s P95 end-to-end |

---

## 3. Export Flow

```
 +-------------------------------------------------------------------+
 | User clicks "Export" in Coding Workspace or Audit Trail            |
 |                                                                   |
 | POST /api/v1/exports                                              |
 | {                                                                 |
 |   "format": "pdf",                                                |
 |   "scope": "session",             // or "date_range", "all"       |
 |   "session_ids": ["uuid1", "uuid2"],                              |
 |   "date_range": null,                                             |
 |   "include_reasoning": true,                                      |
 |   "include_audit_trail": false                                    |
 | }                                                                 |
 +-----------------------------------+-------------------------------+
                                     |
                                     v
 +-----------------------------------+-------------------------------+
 | FastAPI Endpoint                                                  |
 |                                                                   |
 | 1. Validate request (Pydantic)                                    |
 | 2. Authorization: user has "export:read" permission               |
 | 3. Create export job record in PostgreSQL:                        |
 |    - export_id, user_id, tenant_id, format, scope, status="queued"|
 | 4. Dispatch Celery task: generate_export.delay(export_id)         |
 | 5. Return HTTP 202 Accepted with export_id                        |
 +-----------------------------------+-------------------------------+
                                     |
                                     v
 +-----------------------------------+-------------------------------+
 | Celery Worker: generate_export                                    |
 |                                                                   |
 | 1. Update status = "processing"                                   |
 |                                                                   |
 | 2. Query coding data (tenant-scoped via RLS):                     |
 |    - CodingSessions matching scope criteria                       |
 |    - CodingResults for each session                               |
 |    - Audit logs if requested                                      |
 |                                                                   |
 | 3. Generate file based on format:                                 |
 |                                                                   |
 |    PDF:                                                           |
 |    - Render HTML template with Jinja2                             |
 |    - Convert to PDF with WeasyPrint                               |
 |    - Include: header, patient encounter summary, code table,      |
 |      reasoning notes, coding guidelines cited, footer             |
 |                                                                   |
 |    CSV:                                                           |
 |    - Headers: session_id, date, clinical_summary, code,           |
 |      description, confidence, status, coder, notes               |
 |    - One row per code per session                                 |
 |    - UTF-8 with BOM for Excel compatibility                       |
 |                                                                   |
 |    JSON:                                                          |
 |    - Structured JSON matching CodingSuggestResponse schema        |
 |    - Array of session objects with full detail                    |
 |                                                                   |
 |    HL7 FHIR:                                                      |
 |    - FHIR R4 Bundle containing DiagnosticReport resources         |
 |    - Each coding session maps to one DiagnosticReport             |
 |    - ICD-10-CM codes as CodeableConcept with system URI           |
 |      "http://hl7.org/fhir/sid/icd-10-cm"                        |
 |                                                                   |
 | 4. Upload to S3:                                                  |
 |    - Bucket: autocode-exports-{env}                               |
 |    - Key: {tenant_id}/{year}/{month}/{export_id}.{ext}            |
 |    - Encryption: SSE-KMS with tenant-specific key                 |
 |    - Metadata: content-type, export_id, user_id                   |
 |                                                                   |
 | 5. Generate pre-signed download URL (15-minute expiry)            |
 |                                                                   |
 | 6. Update export record:                                          |
 |    - status = "completed"                                         |
 |    - s3_key, file_size, download_url, completed_at                |
 |                                                                   |
 | 7. Audit log:                                                     |
 |    - action: "export_generated"                                   |
 |    - format, scope, record_count, file_size                       |
 +-----------------------------------+-------------------------------+
                                     |
                                     v
 +-----------------------------------+-------------------------------+
 | Client Notification                                               |
 |                                                                   |
 | Option A: WebSocket push notification                             |
 |   - Server sends: { export_id, status: "completed", download_url }|
 |                                                                   |
 | Option B: Client polling                                          |
 |   - GET /api/v1/exports/{export_id}                               |
 |   - Returns status + download_url when completed                  |
 +-----------------------------------+-------------------------------+
                                     |
                                     v
 +-----------------------------------+-------------------------------+
 | Download                                                          |
 |                                                                   |
 | GET /api/v1/exports/{export_id}/download                          |
 |                                                                   |
 | 1. Verify user authorization (same user or admin)                 |
 | 2. Check export status = "completed"                              |
 | 3. Generate fresh pre-signed URL if expired                       |
 | 4. Redirect to S3 pre-signed URL (HTTP 302)                       |
 | 5. Audit log: action = "export_downloaded"                        |
 +-------------------------------------------------------------------+
```

### 3.1 Export Retention Policy

| Item | Policy |
|---|---|
| Export files in S3 | Retained for 90 days, then auto-deleted via S3 lifecycle rule |
| Export metadata in PostgreSQL | Retained indefinitely for audit trail |
| Pre-signed download URLs | Expire after 15 minutes; regenerated on demand |
| Maximum file size | 50MB per export (enforced in Celery worker) |
| Concurrent exports per tenant | Maximum 5 queued/processing exports |

---

## 4. Audit Logging Flow

All system actions that involve PHI access, coding decisions, or administrative changes are captured in an immutable audit log.

### 4.1 Audit Event Categories

| Category | Events | Data Captured |
|---|---|---|
| **Authentication** | Login, logout, token refresh, failed login | user_id, IP, user_agent, success/failure, MFA method |
| **Coding** | Suggest request, code acceptance, code rejection, manual code add | session_id, clinical_text_hash, codes, model, latency |
| **Export** | Export requested, generated, downloaded | export_id, format, scope, record_count, file_size |
| **Search** | Code search, index lookup | query (sanitized), result_count, codes_viewed |
| **Admin** | User created/modified, role changed, tenant settings changed | target_user_id, changes, admin_user_id |
| **Data** | Ingestion started/completed, validation results | version_year, chunk_count, duration, errors |
| **Access** | Patient data viewed, coding session viewed | session_id, accessed_fields |

### 4.2 Audit Log Architecture

```
 +---------------------------------------------------------------------+
 | Any System Action                                                   |
 |                                                                     |
 | Examples:                                                           |
 | - User submits coding request                                       |
 | - User downloads export                                             |
 | - Admin changes user role                                           |
 +-----------------------------------+---------------------------------+
                                     |
                                     v
 +-----------------------------------+---------------------------------+
 | AuditLogger Service                                                 |
 |                                                                     |
 | audit_logger.log(                                                   |
 |   action="coding_suggest",                                          |
 |   user_id=request.state.user_id,                                    |
 |   tenant_id=request.state.tenant_id,                                |
 |   resource_type="coding_session",                                   |
 |   resource_id=session_id,                                           |
 |   details={                                                         |
 |     "codes_suggested": ["J45.42", "J30.9"],                         |
 |     "model": "claude-sonnet-4-20250514",                            |
 |     "latency_ms": 3200,                                             |
 |     "chunk_count": 20                                               |
 |   },                                                                |
 |   ip_address=request.client.host,                                   |
 |   user_agent=request.headers["user-agent"]                          |
 | )                                                                   |
 +-----------------------------------+---------------------------------+
                                     |
                   +-----------------+------------------+
                   |                                    |
                   v                                    v
 +-----------------+------------------+  +--------------+--------------+
 | PostgreSQL: audit_logs table       |  | CloudWatch Logs             |
 |                                    |  |                             |
 | id: UUID (PK)                      |  | Log group:                  |
 | tenant_id: UUID (RLS)              |  |   /autocode/audit           |
 | user_id: UUID                      |  |                             |
 | action: VARCHAR                    |  | Structured JSON log entry   |
 | resource_type: VARCHAR             |  | for centralized monitoring  |
 | resource_id: UUID                  |  | and alerting                |
 | details: JSONB                     |  |                             |
 | ip_address: INET                   |  | Retention: 365 days         |
 | user_agent: TEXT                   |  |                             |
 | created_at: TIMESTAMPTZ           |  | CloudWatch alarms on:       |
 |                                    |  | - Failed login count > 5/min|
 | Index: (tenant_id, created_at)     |  | - Export rate > 10/hour     |
 | Index: (user_id, action)           |  | - Admin action anomalies    |
 | Index: (action, created_at)        |  |                             |
 |                                    |  |                             |
 | Partitioned by month               |  |                             |
 | (created_at range partitioning)    |  |                             |
 +------------------------------------+  +-----------------------------+
```

### 4.3 Audit Log Immutability

The audit_logs table is designed to be append-only:

```sql
-- No UPDATE or DELETE permissions for application role
REVOKE UPDATE, DELETE ON audit_logs FROM app_user;

-- Only the audit_writer role can INSERT
GRANT INSERT ON audit_logs TO audit_writer;

-- Trigger to prevent any UPDATE or DELETE (defense in depth)
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit log records cannot be modified or deleted';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_immutable
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_modification();
```

### 4.4 PHI Handling in Audit Logs

Clinical text is **never** stored directly in audit logs. Instead:

- `clinical_text_hash`: SHA-256 hash of the clinical text (for correlation, not reconstruction)
- `codes_suggested` / `codes_accepted`: ICD-10-CM codes only (not PHI)
- `patient_context`: Age range and sex only (not identifying)
- The actual clinical text is stored only in the `coding_sessions` table (tenant-scoped, RLS-protected)

### 4.5 Audit Log Retention

| Environment | PostgreSQL Retention | CloudWatch Retention |
|---|---|---|
| Production | 7 years (HIPAA requirement: 6 years minimum) | 365 days |
| Staging | 90 days | 30 days |
| Development | 30 days | 7 days |

Partitioned tables enable efficient purging of old partitions beyond the retention period.

### 4.6 Audit Log Query API

```
GET /api/v1/audit
Query parameters:
  - action: filter by action type
  - user_id: filter by user (admin only)
  - resource_type: filter by resource
  - date_from / date_to: date range
  - page / page_size: pagination

Response: paginated list of audit entries (tenant-scoped via RLS)

Access: admin and compliance roles only
```
