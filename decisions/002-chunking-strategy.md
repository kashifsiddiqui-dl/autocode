# ADR-002: Code-Centric Chunking Strategy for ICD-10-CM Data

**Date:** 2026-06-16
**Status:** Accepted
**Deciders:** Engineering Team

## Context

The ICD-10-CM classification system is a hierarchically structured code set, not prose documentation. Traditional RAG chunking strategies (fixed-size, sentence-based, paragraph-based, or recursive text splitting) are designed for narrative text and fundamentally misalign with this data:

- **A code is the atomic unit.** "E11.22" (Type 2 diabetes mellitus with diabetic chronic kidney disease) is a discrete, self-contained concept. Splitting it across chunks or merging it with unrelated codes destroys meaning.
- **Context is inherited.** Code E11.22 inherits excludes notes from E11 (its parent category), which inherits from the E08-E13 section, which inherits from Chapter 4. A chunk that contains only the leaf code's text is missing critical coding instructions.
- **Relationships are structural, not textual.** Excludes1/Excludes2 notes, Code First/Use Additional directives, and 7th character requirements are not narrative paragraphs -- they are machine-interpretable constraints that must be preserved intact.
- **Multiple entry points exist.** A clinician searching for "adult-onset diabetes with kidney complications" should find E11.22 whether they search via the tabular list, the alphabetic index, the drug table, or the neoplasm table.

The ICD-10-CM April 2026 dataset contains:

| Source | Estimated Entry Count | Description |
|---|---|---|
| Tabular list (billable codes) | ~74,000 | Leaf-level codes valid for billing |
| Tabular list (category/subcategory codes) | ~6,000 | Parent codes (3-5 characters, not billable) |
| Alphabetic index entries | ~50,000 | Cross-reference terms pointing to codes |
| Drug/chemical table entries | ~3,000 | Substance-to-code mappings with intent columns |
| Neoplasm table entries | ~2,000 | Anatomical site-to-neoplasm code mappings |
| **Total** | **~130,000-135,000** | |

## Decision

Use a **code-centric chunking strategy** where each chunk represents one logical entry from the ICD-10-CM data, enriched with its full inherited context. No traditional text splitting is applied.

### Chunk Types

#### 1. Billable Code Chunks (~74K)

Each billable (leaf) code becomes one chunk. The chunk text is assembled by walking the hierarchy upward and concatenating all inherited context:

```
Code: E11.22
Description: Type 2 diabetes mellitus with diabetic chronic kidney disease

Parent Chain:
  E11.2 - Type 2 diabetes mellitus with kidney complications
  E11 - Type 2 diabetes mellitus
  E08-E13 - Diabetes mellitus
  Chapter 4 - Endocrine, nutritional and metabolic diseases

Includes (inherited from E11):
  - Type 2 diabetes mellitus
  - diabetes (mellitus) due to insulin secretory defect
  - diabetes NOS
  - insulin resistant diabetes (mellitus)

Excludes1 (inherited from E11):
  - diabetes mellitus due to underlying condition (E08.-)
  - drug or chemical induced diabetes mellitus (E09.-)
  - gestational diabetes (O24.4-)
  - neonatal diabetes mellitus (P70.2)
  - type 1 diabetes mellitus (E10.-)

Use Additional Code:
  - Use additional code to identify control using insulin (Z79.4)
  - Use additional code to identify control using oral antidiabetic drugs (Z79.84)
  - Use additional code to identify control using oral hypoglycemic drugs (Z79.84)

7th Character: Not applicable

Billable: Yes
```

**Payload metadata** stored alongside the chunk:
- `code`: "E11.22"
- `code_type`: "billable_code"
- `chapter`: "4"
- `chapter_title`: "Endocrine, nutritional and metabolic diseases"
- `section`: "E08-E13"
- `section_title`: "Diabetes mellitus"
- `is_billable`: true
- `hierarchy_depth`: 5 (chapter > section > category > subcategory > code)
- `parent_code`: "E11.2"
- `parent_chain`: ["E11.2", "E11", "E08-E13"]
- `has_7th_char`: false
- `excludes1_codes`: ["E08", "E09", "O24.4", "P70.2", "E10"]
- `excludes2_codes`: []
- `source_file`: "tabular"

#### 2. Category/Subcategory Code Chunks (~6K)

Non-billable parent codes are also chunked individually. These serve two purposes:
- They catch queries where the user's description matches a broad category rather than a specific code.
- They surface the "this code is not billable, see children" guidance.

These chunks include the same inherited context plus a note: "This code is not billable. See child codes: E11.21, E11.22, E11.29, ..."

#### 3. Alphabetic Index Entry Chunks (~50K)

Each main term entry from the alphabetic index becomes a chunk. These capture the natural-language synonyms and alternate phrasings that clinicians use:

```
Index Term: Diabetes, diabetic (mellitus) (sugar)
  - with kidney complications - see E11.2-
  - with chronic kidney disease - see E11.22
  - adult-onset - see E11
  - brittle - see E10
  ...

Payload:
  code_type: "index_entry"
  referenced_codes: ["E11.2", "E11.22", "E11", "E10"]
  main_term: "Diabetes"
```

Index entries are critical for recall. A clinician may describe a condition using terminology that does not appear in the tabular list description but is present in the index.

#### 4. Drug/Chemical Table Entry Chunks (~3K)

Each substance row from the Table of Drugs and Chemicals becomes a chunk:

```
Substance: Acetaminophen
  Poisoning - Accidental: T39.1X1A
  Poisoning - Intentional Self-Harm: T39.1X2A
  Poisoning - Assault: T39.1X3A
  Poisoning - Undetermined: T39.1X4A
  Adverse Effect: T39.1X5A
  Underdosing: T39.1X6A

Payload:
  code_type: "drug_entry"
  substance_name: "Acetaminophen"
  referenced_codes: ["T39.1X1A", "T39.1X2A", ...]
```

#### 5. Neoplasm Table Entry Chunks (~2K)

Each anatomical site row from the Neoplasm Table becomes a chunk:

```
Site: Lung, upper lobe
  Malignant Primary: C34.10
  Malignant Secondary: C78.00
  Ca in situ: D02.20
  Benign: D14.30
  Uncertain Behavior: D38.1
  Unspecified Behavior: D49.1

Payload:
  code_type: "neoplasm_entry"
  anatomical_site: "Lung, upper lobe"
  referenced_codes: ["C34.10", "C78.00", ...]
```

### Embedding Strategy per Chunk

Each chunk produces two named vectors in Qdrant (see ADR-003):

1. **`description` vector** (OpenAI text-embedding-3-large, 1024d) - Embedded from the code description / index term / substance name. Optimized for matching user queries that describe a condition in natural language.
2. **`clinical_context` vector** (PubMedBERT, 768d) - Embedded from the full context text (includes, excludes, instructions, parent chain). Optimized for matching clinical nuance and coding rules.

Plus one sparse vector for hybrid BM25 search on the combined text.

## Alternatives Considered

### Fixed-Size Text Chunking (500-1000 tokens)
- **Rejected.** Splitting the tabular list into 500-token windows would place unrelated codes in the same chunk and split related context (e.g., a code's excludes notes) across chunks. Completely inappropriate for structured code data.

### Section-Level Chunking
- **Rejected.** Chunking at the section level (e.g., all of E08-E13 as one chunk) produces chunks that are too large (thousands of tokens) and too broad. Retrieval would return the entire diabetes section for any diabetes query, requiring the LLM to sift through irrelevant codes.

### Hierarchical Chunking (Parent + Children in One Chunk)
- **Considered but rejected as primary strategy.** While grouping E11 with all its children preserves relationships, it creates very large chunks (E11 has ~50 child codes). The LLM would need to extract the relevant code from a large block. Instead, we achieve the same contextual richness by inheriting parent context downward into each leaf chunk.

### No Index/Drug/Neoplasm Chunks (Tabular Only)
- **Rejected.** The alphabetic index contains ~50K synonym/alternate-phrasing entries that do not appear in the tabular descriptions. Omitting them would severely hurt recall for natural-language queries. Similarly, drug and neoplasm tables provide structured lookup paths that clinicians rely on.

## Consequences

### Positive
- **Every chunk is a complete, self-contained coding unit.** No post-retrieval assembly or cross-chunk joins needed.
- **Inherited context prevents coding errors.** Excludes1 notes (mutual exclusions) are present on every child code, so the LLM always sees them.
- **Multiple entry points maximize recall.** The same code (e.g., E11.22) can be found via its tabular description, index synonyms, or parent category match.
- **Payload metadata enables precise filtering.** Searches can be scoped to billable codes only, specific chapters, or specific code types.

### Negative
- **~130K chunks is a large collection.** Ingestion takes meaningful time and the embedding cost for 130K chunks through OpenAI and PubMedBERT is non-trivial (estimated ~$15-25 for initial ingestion).
- **Context duplication.** Parent context (excludes, includes) is duplicated across all children. A category with 50 children means 50 copies of the same excludes text. This is an intentional trade-off: storage is cheap, retrieval correctness is not.
- **Index entries may introduce noise.** Some index entries are vague ("Condition NOS - see X") and may match too broadly. Will need relevance tuning and possibly a confidence threshold.
- **Re-ingestion required for annual updates.** ICD-10-CM is updated annually (October) and sometimes mid-year (April). The entire pipeline must re-run, which is acceptable given the ~30-minute expected runtime.

### Mitigations
- Implement a chunking pipeline that reads directly from the XML source files (tabular, index, drug, neoplasm) and produces structured chunk objects.
- Cache embeddings keyed by chunk content hash so unchanged codes are not re-embedded on updates.
- Apply relevance score thresholds at retrieval time to filter low-confidence matches.
- Log retrieval results for ongoing quality analysis and chunk tuning.

## References

- ICD-10-CM April 2026 XML files in `data/ICD-10-CM/icd10cm-April-1-2026-XML/`
- ICD-10-CM Official Guidelines for Coding and Reporting (April 2026)
- ADR-001: Vector Database Selection (Qdrant)
- ADR-003: Embedding Model Selection
