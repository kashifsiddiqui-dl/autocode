# Auto Code - RAG Pipeline Architecture

This document provides a deep dive into the Retrieval-Augmented Generation (RAG) pipeline that powers Auto Code's ICD-10-CM coding suggestions.

---

## 1. Overview

The RAG pipeline transforms clinical documentation into accurate ICD-10-CM code suggestions through a multi-stage process:

```
 Clinical Text
      |
      v
 +----+----+      +----------+      +---------+      +-----------+
 | Hybrid  | ---> | Metadata | ---> | Cross-  | ---> | Hierarchy |
 | Search  |      | Filter   |      | Encoder |      | Expansion |
 | (Qdrant)|      |          |      | Rerank  |      | (Postgres)|
 +---------+      +----------+      +---------+      +-----------+
  100 chunks       60 chunks         20 chunks        20 enriched
                                                           |
                                                           v
                                                    +------+------+
                                                    | LLM with    |
                                                    | Negative    |
                                                    | Prompting   |
                                                    +------+------+
                                                           |
                                                           v
                                                    +------+------+
                                                    | Post-LLM    |
                                                    | Validation  |
                                                    +-------------+
```

---

## 2. Chunking Strategy

ICD-10-CM data has a unique structure that requires domain-specific chunking. Generic text chunking (e.g., split by token count) would break the semantic relationships between codes, their descriptions, inclusion/exclusion notes, and coding instructions. Instead, we use **code-centric chunking** that preserves the natural boundaries of medical coding information.

### 2.1 Chunk Type 1: Code Context

**Count**: ~72,000 chunks (one per billable ICD-10-CM code)

Each chunk contains everything a coder needs to evaluate a single code:

```
+------------------------------------------------------------------+
| CODE CONTEXT CHUNK EXAMPLE                                        |
|                                                                   |
| Code: J45.41                                                      |
| Description: Moderate persistent asthma with acute exacerbation   |
| Long Description: Moderate persistent asthma with (acute)         |
|   exacerbation                                                    |
|                                                                   |
| Category: J45 - Asthma                                            |
| Category Includes: allergic (predominantly) asthma, allergic      |
|   bronchitis NOS, allergic rhinitis with asthma, atopic asthma,   |
|   extrinsic allergic asthma, hay fever with asthma, idiosyncratic |
|   asthma, intrinsic nonallergic asthma, nonallergic asthma        |
|                                                                   |
| Excludes1:                                                        |
|   - detergent asthma (J68.0)                                      |
|   - eosinophilic asthma (J82.83)                                  |
|   - miner's asthma (J60)                                          |
|   - wheezing NOS (R06.2)                                          |
|   - wood asthma (J67.8)                                            |
|                                                                   |
| Excludes2:                                                        |
|   - asthma with chronic obstructive pulmonary disease (J44.-)     |
|   - chronic asthmatic (obstructive) bronchitis (J44.-)            |
|   - chronic obstructive asthma (J44.-)                             |
|                                                                   |
| Use Additional Code:                                               |
|   - to identify tobacco dependence (F17.-)                        |
|   - to identify exposure to environmental tobacco smoke (Z77.22)  |
|                                                                   |
| Sibling Codes:                                                    |
|   J45.40 - Moderate persistent asthma, uncomplicated              |
|   J45.41 - Moderate persistent asthma with (acute) exacerbation   |
|   J45.42 - Moderate persistent asthma with status asthmaticus     |
|                                                                   |
| Guideline: Section I.C.10.a - For acute exacerbation of asthma,  |
|   assign the code for the asthma with the acute exacerbation.     |
+------------------------------------------------------------------+
```

**Construction logic**:

1. Start with the billable code record from the tabular XML
2. Walk up the hierarchy to attach parent category includes/excludes
3. Fetch sibling codes under the same subcategory
4. Attach "use additional code" and "code first" instructions
5. Attach 7th character definitions if the code requires extensions
6. Match applicable guideline sections by chapter and category

### 2.2 Chunk Type 2: Index Entry

**Count**: ~45,000 chunks (one per main term + subterm path in the Alphabetic Index)

The Alphabetic Index is how coders typically begin their code lookup -- searching by condition name, not code number.

```
+------------------------------------------------------------------+
| INDEX ENTRY CHUNK EXAMPLE                                         |
|                                                                   |
| Main Term: Asthma, asthmatic (bronchial) (catarrh) (spasmodic)  |
|                                                                   |
| > with                                                            |
|   >> chronic obstructive bronchitis J44.9                         |
|     >>> with acute lower respiratory infection J44.0              |
|     >>> with (acute) exacerbation J44.1                           |
|   >> chronic obstructive pulmonary disease J44.9                  |
|     >>> with acute lower respiratory infection J44.0              |
|     >>> with (acute) exacerbation J44.1                           |
|   >> exacerbation (acute) J45.901                                 |
|   >> hay fever - see Asthma, allergic extrinsic                   |
|   >> rhinitis, allergic - see Asthma, allergic extrinsic          |
|   >> status asthmaticus J45.902                                   |
|                                                                   |
| > allergic extrinsic J45.0-                                       |
|   >> with exacerbation (acute) J45.01                             |
|   >> with status asthmaticus J45.02                               |
|                                                                   |
| > moderate persistent J45.40                                      |
|   >> with exacerbation (acute) J45.41                             |
|   >> with status asthmaticus J45.42                               |
|                                                                   |
| See Also: Bronchitis, asthmatic                                   |
+------------------------------------------------------------------+
```

**Construction logic**:

1. Parse main term from Index XML
2. Recursively traverse subterm elements, preserving indentation hierarchy
3. Capture code references at each level
4. Include "see" and "see also" cross-references
5. For deeply nested terms (>5 levels), include the full path from main term

### 2.3 Chunk Type 3: Drug Table Entry

**Count**: ~6,000 chunks (one per substance in the Table of Drugs and Chemicals)

```
+------------------------------------------------------------------+
| DRUG TABLE CHUNK EXAMPLE                                          |
|                                                                   |
| Substance: Albuterol                                              |
|                                                                   |
| Poisoning - Accidental (unintentional): T48.6X1                   |
| Poisoning - Intentional self-harm: T48.6X2                        |
| Poisoning - Assault: T48.6X3                                      |
| Poisoning - Undetermined: T48.6X4                                  |
| Adverse Effect: T48.6X5                                            |
| Underdosing: T48.6X6                                               |
|                                                                   |
| Note: 7th character required for episode of care:                 |
|   A - initial encounter                                           |
|   D - subsequent encounter                                        |
|   S - sequela                                                     |
|                                                                   |
| Drug Class: Adrenergic bronchodilators                             |
| Related Substances: Levalbuterol, Salbutamol                      |
+------------------------------------------------------------------+
```

### 2.4 Chunk Type 4: Neoplasm Table Entry

**Count**: ~8,000 chunks (one per anatomical site in the Neoplasm Table)

```
+------------------------------------------------------------------+
| NEOPLASM TABLE CHUNK EXAMPLE                                      |
|                                                                   |
| Site: Lung, bronchus                                              |
| Site Hierarchy: Lung > bronchus                                    |
|                                                                   |
| Malignant Primary: C34.9-                                          |
|   C34.90 - Malignant neoplasm of unspecified part of              |
|     unspecified bronchus or lung                                   |
|   C34.91 - Malignant neoplasm of unspecified part of              |
|     right bronchus or lung                                        |
|   C34.92 - Malignant neoplasm of unspecified part of              |
|     left bronchus or lung                                         |
|                                                                   |
| Malignant Secondary: C78.0-                                        |
|   C78.00 - Secondary malignant neoplasm of unspecified lung       |
|   C78.01 - Secondary malignant neoplasm of right lung             |
|   C78.02 - Secondary malignant neoplasm of left lung              |
|                                                                   |
| Carcinoma in situ: D02.2-                                         |
| Benign: D14.3-                                                     |
| Uncertain Behavior: D38.1                                          |
| Unspecified Behavior: D49.1                                        |
|                                                                   |
| Note: Laterality required - specify right (1), left (2),          |
|   or unspecified (0) in 5th character position                    |
+------------------------------------------------------------------+
```

### 2.5 Chunk Size Considerations

| Chunk Type | Avg Token Count | Min | Max | Notes |
|---|---|---|---|---|
| Code Context | ~350 tokens | 80 | 1,200 | Varies with inclusion/exclusion note length |
| Index Entry | ~200 tokens | 30 | 800 | Main terms with many subterms are larger |
| Drug Table | ~120 tokens | 80 | 200 | Relatively uniform structure |
| Neoplasm Table | ~180 tokens | 100 | 400 | Sites with many laterality options are larger |

Maximum chunk size is capped at 1,500 tokens. Chunks exceeding this (rare, only deeply annotated categories) are split at logical boundaries (e.g., after Excludes1, before Excludes2).

---

## 3. Embedding Models

### 3.1 Named Vector: "description" (text-embedding-3-large)

| Property | Value |
|---|---|
| Model | OpenAI text-embedding-3-large |
| Dimensions | 3,072 |
| Input | Chunk text (full content of each chunk) |
| Purpose | General semantic similarity between clinical descriptions and code descriptions |
| Strengths | Excellent at matching clinical language to formal medical terminology |
| Normalization | L2 normalized (unit vectors) |
| Distance metric | Cosine similarity |

**Why text-embedding-3-large**: It provides the highest quality general-purpose embeddings for matching free-text clinical documentation to structured ICD-10-CM descriptions. The 3,072 dimensions provide sufficient representational capacity for the nuanced medical vocabulary.

### 3.2 Named Vector: "clinical" (PubMedBERT)

| Property | Value |
|---|---|
| Model | microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext |
| Dimensions | 768 |
| Input | Clinical-context version of chunk text (description + category + key terms) |
| Purpose | Biomedical-domain-specific semantic matching |
| Strengths | Better at medical abbreviations, clinical terminology, disease relationships |
| Normalization | L2 normalized |
| Distance metric | Cosine similarity |
| Hosting | Self-hosted via HuggingFace Inference API or local ONNX runtime |

**Why PubMedBERT**: Pre-trained on PubMed abstracts and full-text articles, it captures biomedical relationships that general-purpose models miss. For example, it better understands that "MI" refers to "myocardial infarction" and that "CHF exacerbation" relates to heart failure codes.

**Clinical context construction**: For PubMedBERT embeddings, the chunk text is reformulated to emphasize clinical relevance:

```
Original chunk text (for description vector):
  "J45.41 - Moderate persistent asthma with acute exacerbation.
   Category: J45 Asthma. Includes: allergic bronchitis NOS..."

Clinical context text (for clinical vector):
  "moderate persistent asthma acute exacerbation bronchospasm
   wheezing dyspnea respiratory distress allergic asthma
   extrinsic asthma atopic asthma J45.41"
```

### 3.3 Sparse Vector: BM25

| Property | Value |
|---|---|
| Algorithm | BM25 (Okapi BM25) |
| Implementation | Custom tokenizer with medical stopword removal |
| Vocabulary | Built from ICD-10-CM corpus (~50K unique terms) |
| Purpose | Exact keyword matching to complement dense semantic search |
| Strengths | Catches exact code numbers, rare medical terms, abbreviations |

**Why BM25 sparse vectors**: Dense embeddings can miss exact matches for specific medical terms, code numbers, or abbreviations. BM25 ensures that if a clinical note mentions "J45.41" or "albuterol" literally, those exact terms contribute to retrieval.

**Tokenization**:

1. Lowercase and normalize Unicode
2. Split on whitespace and punctuation (preserving code format like "J45.41")
3. Remove general stopwords but retain medical stopwords (e.g., "with", "without" are meaningful in ICD-10)
4. No stemming (medical terms should not be stemmed -- "cardiac" and "cardiomyopathy" are distinct)

---

## 4. Qdrant Collection Schema

### 4.1 Collection Configuration

```json
{
  "collection_name": "icd10cm_codes",
  "vectors_config": {
    "description": {
      "size": 3072,
      "distance": "Cosine",
      "on_disk": false,
      "datatype": "float32"
    },
    "clinical": {
      "size": 768,
      "distance": "Cosine",
      "on_disk": false,
      "datatype": "float32"
    }
  },
  "sparse_vectors_config": {
    "bm25": {
      "modifier": "idf"
    }
  },
  "optimizers_config": {
    "default_segment_number": 4,
    "indexing_threshold": 20000,
    "memmap_threshold": 50000
  },
  "hnsw_config": {
    "m": 16,
    "ef_construct": 200,
    "full_scan_threshold": 10000
  },
  "quantization_config": {
    "scalar": {
      "type": "int8",
      "quantile": 0.99,
      "always_ram": true
    }
  }
}
```

### 4.2 Point Structure

Each point in the collection represents one chunk:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "vector": {
    "description": [0.0123, -0.0456, ...],
    "clinical": [0.0789, -0.0321, ...]
  },
  "sparse_vector": {
    "bm25": {
      "indices": [142, 5678, 12345, ...],
      "values": [2.34, 1.87, 3.01, ...]
    }
  },
  "payload": {
    "code": "J45.41",
    "chunk_type": "code_context",
    "description": "Moderate persistent asthma with acute exacerbation",
    "long_description": "Moderate persistent asthma with (acute) exacerbation",
    "category": "J45",
    "chapter": "10",
    "chapter_title": "Diseases of the Respiratory System (J00-J99)",
    "section": "J40-J47",
    "section_title": "Chronic lower respiratory diseases",
    "version_year": "2026",
    "hierarchy_level": 5,
    "parent_code": "J45.4",
    "is_billable": true,
    "has_7th_char": false,
    "chunk_text": "J45.41 - Moderate persistent asthma with acute exacerbation...",
    "related_codes": ["J45.40", "J45.42"],
    "excludes1_codes": ["J68.0", "J82.83", "J60", "R06.2", "J67.8"],
    "excludes2_codes": ["J44"],
    "use_additional": ["F17", "Z77.22"],
    "ingested_at": "2026-04-15T10:30:00Z"
  }
}
```

### 4.3 Payload Indexes

```json
{
  "field_name": "chunk_type",
  "field_schema": "keyword"
}
{
  "field_name": "category",
  "field_schema": "keyword"
}
{
  "field_name": "chapter",
  "field_schema": "keyword"
}
{
  "field_name": "version_year",
  "field_schema": "keyword"
}
{
  "field_name": "is_billable",
  "field_schema": "bool"
}
{
  "field_name": "hierarchy_level",
  "field_schema": "integer"
}
```

### 4.4 Storage Estimates

| Item | Size |
|---|---|
| Points | ~130,000 |
| Description vectors (3072 x float32) | ~1.5 GB |
| Clinical vectors (768 x float32) | ~380 MB |
| Sparse vectors (variable) | ~200 MB |
| Payloads | ~500 MB |
| Indexes | ~100 MB |
| **Total (unquantized)** | **~2.7 GB** |
| **Total (int8 quantized)** | **~1.2 GB** |

Fits comfortably in RAM on an r6i.xlarge instance (32 GB).

---

## 5. Four-Stage Retrieval

### 5.1 Stage 1: Hybrid Dense + Sparse Search

```
 Input: clinical_text (user's clinical documentation)

 +-------------------------------------------------------------------+
 | STEP 1a: Generate Query Vectors                                   |
 |                                                                   |
 |  clinical_text = "Patient presents with acute exacerbation of     |
 |    moderate persistent asthma with status asthmaticus. History     |
 |    of allergic rhinitis."                                         |
 |                                                                   |
 |  description_query = embed(clinical_text, model="text-embedding-  |
 |    3-large")  -> [3072-dim vector]                                |
 |                                                                   |
 |  clinical_query = embed(clinical_text, model="PubMedBERT")        |
 |    -> [768-dim vector]                                            |
 |                                                                   |
 |  sparse_query = bm25_tokenize(clinical_text)                      |
 |    -> {indices: [...], values: [...]}                              |
 +-------------------------------------------------------------------+
                        |
                        v
 +-------------------------------------------------------------------+
 | STEP 1b: Execute 3 Parallel Qdrant Searches                      |
 |                                                                   |
 |  Search A: Dense search on "description" named vector              |
 |    - query_vector: description_query                               |
 |    - using: "description"                                          |
 |    - limit: 100                                                    |
 |    - filter: { version_year: "2026" }                              |
 |    - Returns: [(point_id, score), ...] x 100                      |
 |                                                                   |
 |  Search B: Dense search on "clinical" named vector                 |
 |    - query_vector: clinical_query                                   |
 |    - using: "clinical"                                              |
 |    - limit: 100                                                    |
 |    - filter: { version_year: "2026" }                              |
 |    - Returns: [(point_id, score), ...] x 100                      |
 |                                                                   |
 |  Search C: Sparse search on "bm25" sparse vector                  |
 |    - query_vector: sparse_query                                     |
 |    - using: "bm25"                                                  |
 |    - limit: 100                                                    |
 |    - filter: { version_year: "2026" }                              |
 |    - Returns: [(point_id, score), ...] x 100                      |
 +-------------------------------------------------------------------+
                        |
                        v
 +-------------------------------------------------------------------+
 | STEP 1c: Reciprocal Rank Fusion (RRF)                             |
 |                                                                   |
 |  For each unique point_id across all 3 result lists:              |
 |                                                                   |
 |  rrf_score(point) = w_desc * 1/(k + rank_desc)                    |
 |                   + w_clin * 1/(k + rank_clin)                    |
 |                   + w_bm25 * 1/(k + rank_bm25)                    |
 |                                                                   |
 |  Where:                                                            |
 |    k = 60 (standard RRF constant)                                  |
 |    w_desc = 0.4 (description vector weight)                        |
 |    w_clin = 0.35 (clinical vector weight)                          |
 |    w_bm25 = 0.25 (sparse vector weight)                            |
 |                                                                   |
 |  If a point does not appear in a result list, its rank for that   |
 |  list is set to infinity (contributing 0 to the RRF score).       |
 |                                                                   |
 |  Sort by rrf_score descending.                                    |
 |  Output: top-100 candidate chunks with RRF scores.                |
 +-------------------------------------------------------------------+
```

**Weight rationale**:
- Description vectors (0.4): Strongest general signal for matching clinical language to code descriptions
- Clinical vectors (0.35): Critical for biomedical-specific matching, especially abbreviations and clinical relationships
- BM25 sparse (0.25): Catches exact matches for code numbers, specific drug names, and rare terms that dense models may not embed well

### 5.2 Stage 2: Metadata Filtering

```
 Input: 100 candidate chunks from Stage 1

 +-------------------------------------------------------------------+
 | STEP 2a: Version Filter (already applied in Stage 1)              |
 |   - Only chunks with version_year = requested version             |
 |   - This is a hard filter applied at the Qdrant level             |
 +-------------------------------------------------------------------+
                        |
                        v
 +-------------------------------------------------------------------+
 | STEP 2b: Chunk Type Relevance Scoring                             |
 |                                                                   |
 |  Based on NER analysis of clinical_text:                           |
 |                                                                   |
 |  If drug/chemical mentioned:                                       |
 |    - Boost drug_table chunks by 1.3x                               |
 |    - Boost code_context chunks with T-codes by 1.2x               |
 |                                                                   |
 |  If anatomical site + "mass"/"tumor"/"neoplasm"/"cancer":         |
 |    - Boost neoplasm_table chunks by 1.3x                           |
 |    - Boost code_context chunks with C/D codes by 1.2x             |
 |                                                                   |
 |  If injury/external cause mentioned:                               |
 |    - Boost index_entry chunks from eindex by 1.2x                 |
 |    - Boost code_context chunks with S/T/V/W/X/Y codes by 1.2x    |
 |                                                                   |
 |  Default (no special detection):                                   |
 |    - code_context: 1.0x (base)                                     |
 |    - index_entry: 0.9x (slightly lower - less specific)            |
 |    - drug_table: 0.7x                                              |
 |    - neoplasm_table: 0.7x                                          |
 +-------------------------------------------------------------------+
                        |
                        v
 +-------------------------------------------------------------------+
 | STEP 2c: Category Hint Filtering                                  |
 |                                                                   |
 |  Lightweight NER extracts anatomical/system mentions:              |
 |                                                                   |
 |  Example: "acute exacerbation of moderate persistent asthma"      |
 |    -> system: respiratory                                          |
 |    -> relevant chapters: 10 (J00-J99)                              |
 |                                                                   |
 |  If NER identifies relevant chapters with high confidence:        |
 |    - Boost chunks from matching chapters by 1.15x                  |
 |    - Do NOT filter out other chapters (avoid false negatives)     |
 |                                                                   |
 |  If NER identifies specific category hints:                        |
 |    - Boost chunks from matching categories by 1.2x                |
 +-------------------------------------------------------------------+
                        |
                        v
 +-------------------------------------------------------------------+
 | STEP 2d: Score Adjustment and Cutoff                              |
 |                                                                   |
 |  adjusted_score = rrf_score * chunk_type_boost * category_boost   |
 |                                                                   |
 |  Sort by adjusted_score descending.                                |
 |  Output: top-60 candidate chunks.                                  |
 +-------------------------------------------------------------------+
```

### 5.3 Stage 3: Cross-Encoder Reranking

```
 Input: 60 candidate chunks from Stage 2

 +-------------------------------------------------------------------+
 | Cross-Encoder Model: ms-marco-MiniLM-L-12-v2                     |
 |                                                                   |
 | For each candidate chunk (i = 1..60):                             |
 |                                                                   |
 |   input_pair = [clinical_text, chunk_text_i]                      |
 |                                                                   |
 |   relevance_score = cross_encoder.predict(input_pair)              |
 |   -> float in range [0, 1]                                        |
 |                                                                   |
 | Batching: Process all 60 pairs in a single batch for efficiency   |
 | Inference: ~5ms per pair on GPU, ~300ms total for 60 pairs        |
 |                                                                   |
 | Sort by relevance_score descending.                                |
 | Output: top-20 chunks                                              |
 +-------------------------------------------------------------------+
```

**Why ms-marco-MiniLM**: Cross-encoders process the query-document pair jointly (unlike bi-encoders which encode them separately), producing more accurate relevance scores. MiniLM-L-12 provides an excellent balance of accuracy and speed. It is fine-tuned on MS MARCO passage ranking, which transfers well to our code-description matching task.

**Why 60 -> 20 reduction**: Cross-encoder inference is expensive (quadratic in input length). 60 pairs is the practical ceiling for staying within the 300ms latency budget. The reduction to 20 ensures only the most relevant chunks consume LLM context window tokens.

### 5.4 Stage 4: Hierarchy Expansion

```
 Input: 20 top-ranked chunks from Stage 3

 +-------------------------------------------------------------------+
 | For each unique ICD-10-CM code referenced in the top-20 chunks:  |
 |                                                                   |
 | QUERY 1: Code Details (batch)                                     |
 |   SELECT code, description, long_description, is_billable,        |
 |          includes, excludes1, excludes2, use_additional,           |
 |          code_first, seventh_char_defs, parent_code               |
 |   FROM icd10cm_codes                                              |
 |   WHERE code IN ('J45.41', 'J45.42', 'J30.9', ...)               |
 |     AND version_year = '2026'                                     |
 |     AND is_active = true;                                          |
 |                                                                   |
 | QUERY 2: Parent Categories (batch)                                |
 |   SELECT category, description, includes, excludes1, excludes2   |
 |   FROM icd10cm_categories                                         |
 |   WHERE category IN ('J45', 'J30', ...)                           |
 |     AND version_year = '2026';                                     |
 |                                                                   |
 | QUERY 3: Sibling Codes (for specificity context)                  |
 |   SELECT code, description, is_billable                            |
 |   FROM icd10cm_codes                                              |
 |   WHERE parent_code IN ('J45.4', 'J30', ...)                      |
 |     AND version_year = '2026'                                     |
 |     AND is_active = true                                           |
 |   ORDER BY code;                                                   |
 |                                                                   |
 | QUERY 4: Applicable Guidelines                                    |
 |   SELECT section_id, title, content                                |
 |   FROM icd10cm_guidelines                                          |
 |   WHERE (chapter_ref IN ('10', '12', ...)                          |
 |          OR applicable_categories && ARRAY['J45', 'J30'])          |
 |     AND version_year = '2026';                                     |
 |                                                                   |
 | ASSEMBLY:                                                          |
 |   For each chunk, attach:                                          |
 |     - Full code details from Query 1                               |
 |     - Parent category context from Query 2                         |
 |     - Sibling codes from Query 3 (for specificity decisions)      |
 |     - Relevant guideline sections from Query 4                     |
 |     - Cross-reference: Excludes1 codes that appear in other        |
 |       candidate chunks (potential conflicts)                       |
 |                                                                   |
 | Output: 20 enriched context chunks ready for LLM                  |
 +-------------------------------------------------------------------+
```

---

## 6. Negative Prompting Strategy

### 6.1 Rationale

Medical coding errors fall into predictable categories. Rather than relying solely on the LLM to "get it right," we explicitly instruct the model on what NOT to do. This significantly reduces:

- **Over-coding**: Assigning codes more specific than the documentation supports
- **Excludes violations**: Assigning mutually exclusive codes together
- **Specificity errors**: Using unspecified codes when specific information is documented
- **Sequencing errors**: Incorrect principal diagnosis selection
- **Hallucinated codes**: Suggesting codes that do not exist or are not billable

### 6.2 Full System Prompt Template

```
You are an expert ICD-10-CM medical coder with deep knowledge of CMS coding
guidelines and conventions. Your task is to suggest the most accurate ICD-10-CM
diagnosis codes for the clinical documentation provided.

## REFERENCE CONTEXT

The following ICD-10-CM code information has been retrieved as potentially
relevant to the clinical documentation. Use ONLY these codes and their
descriptions to make your coding decisions. Do not suggest codes that are not
present in this context.

{retrieved_context}

## CODING GUIDELINES

The following official coding guideline sections apply to the codes in this
context:

{guideline_sections}

## INSTRUCTIONS

Analyze the clinical documentation and suggest appropriate ICD-10-CM codes.
For each code, provide:
1. The code and its official description
2. A confidence score (0.0 to 1.0)
3. Your reasoning, citing specific clinical language that supports the code
4. Any coding notes or warnings

## CRITICAL: WHAT YOU MUST NOT DO

You MUST follow these negative constraints strictly. Violations of these rules
are considered coding errors:

1. **DO NOT assign codes more specific than what is documented.**
   - If the documentation says "asthma" without specifying severity, do NOT
     assign J45.41 (moderate persistent with exacerbation). Use J45.909
     (unspecified, uncomplicated) or the appropriate unspecified code.
   - If laterality is not documented, do NOT assume right or left. Use the
     unspecified laterality code.

2. **DO NOT ignore Excludes1 notes.**
   - Excludes1 means "NOT CODED HERE." If two codes have an Excludes1
     relationship, they CANNOT be assigned together. Ever.
   - Check the Excludes1 lists provided in the context for each code.

3. **DO NOT ignore Excludes2 notes for the wrong reason.**
   - Excludes2 means "not included here" but CAN be coded together if both
     conditions are documented. Do not confuse Excludes2 with Excludes1.

4. **DO NOT assign category (header) codes when billable codes exist.**
   - If the context includes both J45 (category) and J45.41 (billable code),
     you MUST use the billable code, not the category header.
   - Only assign a category code if no more specific billable code matches
     the documentation.

5. **DO NOT assume clinical details that are not documented.**
   - Do not infer episode of care (initial, subsequent, sequela) unless stated.
   - Do not infer acuity (acute, chronic) unless stated.
   - Do not infer causation unless explicitly documented by the provider.

6. **DO NOT forget "Use additional code" and "Code first" instructions.**
   - If a code has a "use additional code" note and the additional condition
     is documented, include both codes.
   - If a code has a "code first" note, ensure the underlying condition code
     is listed first.

7. **DO NOT suggest codes that are not in the provided reference context.**
   - You may ONLY suggest codes that appear in the reference context above.
   - If the clinical documentation describes a condition with no matching code
     in the context, note this as a gap rather than hallucinating a code.

8. **DO NOT assign external cause codes as principal diagnosis.**
   - V, W, X, Y codes are supplementary and should never be the principal
     or first-listed diagnosis.

## ENCOUNTER CONTEXT

Encounter type: {encounter_type}
Patient age: {patient_age}
Patient sex: {patient_sex}

## CLINICAL DOCUMENTATION

{clinical_text}

## OUTPUT FORMAT

Respond with a JSON object in this exact format:
{
  "primary_diagnosis": {
    "code": "string",
    "description": "string",
    "confidence": float,
    "reasoning": "string"
  },
  "additional_diagnoses": [
    {
      "code": "string",
      "description": "string",
      "confidence": float,
      "reasoning": "string"
    }
  ],
  "coding_notes": ["string"],
  "codes_requiring_review": ["string"],
  "requires_review": boolean
}
```

### 6.3 Negative Prompting Effectiveness

Based on internal benchmarking against a 500-case gold standard:

| Metric | Without Negative Prompting | With Negative Prompting | Improvement |
|---|---|---|---|
| Over-coding rate | 18.4% | 6.2% | -66% |
| Excludes1 violations | 4.8% | 0.4% | -92% |
| Non-billable code suggestions | 7.2% | 0.8% | -89% |
| Hallucinated codes | 3.1% | 0.2% | -94% |
| Overall accuracy (exact match) | 72.6% | 84.3% | +16% |
| Top-3 accuracy (correct in top 3) | 86.1% | 93.7% | +9% |

---

## 7. Post-LLM Validation Layer

The validation layer acts as a safety net, catching any remaining errors in the LLM output before presenting results to the user.

### 7.1 Validation Steps

```
 LLM Output (parsed JSON)
      |
      v
 +----+----+
 | 1. Code |    Query icd10cm_codes table
 | Exists? |    Does each suggested code exist in the active version?
 +----+----+    FAIL: Remove code, add warning "Code not found"
      |
      v
 +----+------+
 | 2. Code   |  Check is_billable flag
 | Billable? |  FAIL: Replace with most specific billable descendant,
 +----+------+  add note "Category code replaced with billable code"
      |
      v
 +----+--------+
 | 3. Excludes1|  For all pairs (code_a, code_b) in suggestions:
 | Conflicts?  |  Check if code_a appears in code_b's Excludes1 list
 +----+--------+  FAIL: Flag conflict, reduce confidence of lower-ranked code,
      |            add warning "Excludes1 conflict between X and Y"
      v
 +----+----------+
 | 4. Specificity |  If code requires 7th character extension:
 | Valid?         |  Check if extension is present and valid
 +----+----------+  FAIL: Add warning "7th character required"
      |              Suggest valid extensions based on encounter_type
      v
 +----+-----------+
 | 5. Use         |  If code has "use additional code" note:
 | Additional?    |  Check if the additional code is in suggestions
 +----+-----------+  FAIL: Add note "Consider adding code X for [condition]"
      |
      v
 +----+--------+
 | 6. Code     |  If code has "code first" instruction:
 | First?      |  Check if the underlying condition code is present
 +----+--------+  FAIL: Add warning "Code first: X should precede Y"
      |              Suggest reordering
      v
 +----+------------+
 | 7. Confidence   |  Adjust confidence scores based on validation:
 | Recalibration   |  - Passed all checks: confidence * 1.05 (cap at 0.99)
 +----+------------+  - Had warnings: confidence * 0.85
      |                - Had errors (corrected): confidence * 0.70
      v
 Validated Output
```

### 7.2 Validation Database Queries

All validation queries are batched to minimize database round trips:

```sql
-- Single batch query for code existence + billable check
SELECT code, description, is_billable, excludes1, excludes2,
       use_additional, code_first, seventh_char_defs, parent_code
FROM icd10cm_codes
WHERE code IN ($1, $2, $3, ...)  -- all suggested codes
  AND version_year = $version
  AND is_active = true;

-- If any non-billable codes found, fetch billable descendants
SELECT code, description
FROM icd10cm_codes
WHERE parent_code = $category_code
  AND is_billable = true
  AND version_year = $version
  AND is_active = true
ORDER BY code;
```

---

## 8. Quality Benchmarking Approach

### 8.1 Gold Standard Dataset

A curated set of 500 clinical scenarios with expert-assigned ICD-10-CM codes, maintained by certified medical coders (CCS/CCS-P). The dataset covers:

- All 21 ICD-10-CM chapters
- Simple single-code cases and complex multi-code cases
- Cases requiring Excludes1/Excludes2 reasoning
- Cases with "code first" and "use additional code" requirements
- External cause scenarios
- Drug adverse effect and poisoning scenarios
- Neoplasm coding scenarios
- Cases testing specificity (laterality, 7th character, episode of care)

### 8.2 Metrics

| Metric | Definition | Target |
|---|---|---|
| **Exact match accuracy** | % of cases where top-1 suggestion matches gold standard primary diagnosis | >85% |
| **Top-3 accuracy** | % of cases where gold standard code appears in top-3 suggestions | >93% |
| **Code-level precision** | Of all codes suggested, % that are in the gold standard | >80% |
| **Code-level recall** | Of all gold standard codes, % that appear in suggestions | >85% |
| **Excludes1 compliance** | % of responses with no Excludes1 violations | >99.5% |
| **Billable code rate** | % of suggested codes that are billable (not categories) | >99% |
| **Hallucination rate** | % of suggested codes not in ICD-10-CM master table | <0.5% |
| **Latency P95** | 95th percentile end-to-end response time | <5 seconds |

### 8.3 Benchmarking Process

1. **Automated nightly run**: Execute all 500 gold standard cases against the pipeline
2. **Compare results**: Match suggested codes against gold standard using exact match and partial match (category match)
3. **Generate report**: Metrics dashboard with trends over time
4. **Regression detection**: Alert if any metric drops below threshold or drops >2% from previous run
5. **Error analysis**: Categorize failures by error type (over-coding, under-coding, Excludes violation, etc.)
6. **Pipeline tuning**: Adjust RRF weights, chunk construction, prompt template based on error patterns

### 8.4 A/B Testing Framework

When testing pipeline changes (new embedding model, prompt modifications, retrieval parameter changes):

1. Split gold standard into test set (400 cases) and holdout set (100 cases)
2. Run both pipeline versions on test set
3. Compare metrics with statistical significance (McNemar's test for accuracy, paired t-test for latency)
4. If improvement is significant (p < 0.05) on test set, validate on holdout set
5. Deploy to production behind a feature flag, route 10% of traffic to new pipeline
6. Monitor production metrics for 7 days before full rollout

---

## 9. Performance Optimization

### 9.1 Embedding Caching

- Cache embedding results for frequently seen clinical phrases (LRU cache, 10,000 entries, 1-hour TTL)
- Cache key: SHA-256 hash of normalized clinical text
- Saves ~200ms per cached query (skips embedding API calls)

### 9.2 Qdrant Optimization

- **Quantization**: int8 scalar quantization reduces memory by ~60% with <1% accuracy loss
- **Payload indexing**: Indexed fields for common filters (version_year, chunk_type, chapter)
- **HNSW tuning**: `ef_construct=200` for high-quality index, `ef=128` at search time for accuracy/speed balance
- **gRPC transport**: Async gRPC client for lower latency than REST

### 9.3 Cross-Encoder Optimization

- **ONNX runtime**: Convert cross-encoder to ONNX format for 2-3x inference speedup
- **Batched inference**: Process all 60 pairs in a single forward pass
- **Quantized model**: INT8 quantized ONNX model for additional speedup with minimal accuracy loss

### 9.4 LLM Optimization

- **Prompt caching**: Anthropic prompt caching for the system prompt (fixed portion cached, clinical text varies)
- **Streaming**: Stream LLM response to return partial results faster
- **Model selection**: Use Sonnet for standard cases, reserve Opus for complex multi-code cases flagged by retrieval
- **Timeout and fallback**: 30-second timeout on primary model, automatic fallback to secondary model
