# FEAT-001: Data Ingestion Pipeline

## Status: Not Started
## Priority: P0
## Release: R1 Foundation
## Owner: TBD
## Estimated Effort: 1.5 weeks

---

## Summary

Build a data ingestion pipeline that parses all 5 ICD-10-CM XML source files, loads structured code records into PostgreSQL (~98,186 entries), generates text embeddings using OpenAI text-embedding-3-small, and loads ~130K semantic chunks into Qdrant vector database.

## Problem Statement

The ICD-10-CM coding standard is distributed as XML files with complex, nested structures. Each XML format (tabular, index, drug, neoplasm, external causes index) has a different schema. To power RAG-based retrieval, this raw data must be parsed into structured records for the relational database and semantically chunked for the vector database.

## Functional Requirements

### FR-1: XML Parsing

Parse the following source files from `data/ICD-10-CM/icd10cm-April-1-2026-XML/`:

| File | Parser | Output |
|------|--------|--------|
| `icd10c-tabular-April-1-2026.xml` | TabularParser | Chapters, sections, categories, codes with full hierarchy |
| `icd10cm-index-April-1-2026-XML.xml` | IndexParser | Alphabetical index entries with see/see-also references |
| `icd10cm-drug-April-1-2026-XML.xml` | DrugParser | Drug/substance table with poisoning, adverse effect, underdosing columns |
| `icd10cm-neoplasm-April-1-2026-XML.xml` | NeoplasmParser | Neoplasm table with malignant primary/secondary, in situ, benign, uncertain, unspecified |
| `icd10cm-eindex-April-1-2026-XML.xml` | EIndexParser | External causes of morbidity index |

Each parser must:
- Handle the specific XML schema for its file type
- Extract all codes with their full descriptions
- Preserve hierarchy relationships (chapter > section > category > code)
- Extract includes notes, excludes1 notes, excludes2 notes
- Extract code-first and use-additional annotations
- Handle 7th character extensions (where applicable)
- Report parsing statistics (records processed, errors, warnings)

### FR-2: PostgreSQL Loading

- Create a `coding_standards` record for ICD-10-CM 2026
- Bulk insert all parsed codes into the `codes` table
- Populate all fields: code, description, long_description, chapter, section, category, is_billable, parent_code
- Store includes/excludes/annotations in the `metadata` JSONB column
- Verify count matches expected total (~98,186 codes)
- Create appropriate indexes for query performance

### FR-3: Chunk Generation

Generate text chunks optimized for semantic search:

| Chunk Type | Content Template | Source |
|------------|-----------------|--------|
| `tabular` | "{code} - {description}. {long_description}. Chapter: {chapter_desc}. Section: {section_desc}. {includes}. {excludes1}. {excludes2}." | Tabular XML |
| `index` | "Index entry: {term}. Main term: {main_term}. See: {see_ref}. See also: {see_also_ref}. Codes: {codes}." | Index XML |
| `drug` | "Drug/substance: {name}. Poisoning accidental: {code}. Poisoning intentional: {code}. Adverse effect: {code}. Underdosing: {code}." | Drug XML |
| `neoplasm` | "Neoplasm: {site}. Malignant primary: {code}. Malignant secondary: {code}. In situ: {code}. Benign: {code}. Uncertain: {code}. Unspecified: {code}." | Neoplasm XML |
| `eindex` | "External cause: {term}. {sub_terms}. Codes: {codes}." | EIndex XML |

Chunk constraints:
- Maximum chunk size: 2048 tokens
- Include full hierarchy context in each chunk
- Preserve all clinical annotations (includes, excludes, notes)

### FR-4: Embedding Generation

- Use OpenAI `text-embedding-3-small` model (1536 dimensions)
- Batch size: 100 chunks per API call
- Rate limiting: respect OpenAI API rate limits with exponential backoff
- Progress tracking: log percentage complete every 1000 chunks
- Error handling: retry failed batches up to 3 times, log permanently failed chunks
- Estimated cost: ~130K chunks * ~200 tokens avg = ~26M tokens (~$0.52 at $0.02/1M tokens)

### FR-5: Qdrant Loading

- Create `icd10cm_chunks` collection with cosine distance metric
- Upsert vectors with full payload metadata (code, description, chunk_type, chapter, section, category, is_billable, hierarchy_path, content, standard_id)
- Create payload indexes: chunk_type, chapter, is_billable, standard_id, code
- Batch upsert size: 100 vectors per request
- Verify final collection count matches expected total

### FR-6: Ingestion CLI

- `python scripts/ingest.py` -- full pipeline (parse, load DB, embed, load Qdrant)
- `python scripts/ingest.py --step parse` -- parse XML only, output JSON
- `python scripts/ingest.py --step load-db` -- load parsed data into PostgreSQL
- `python scripts/ingest.py --step embed` -- generate embeddings for chunks
- `python scripts/ingest.py --step load-qdrant` -- load vectors into Qdrant
- `python scripts/ingest.py --validate` -- run validation checks post-ingestion
- `python scripts/ingest.py --standard icd10cm --version 2026` -- specify standard

## Non-Functional Requirements

- **Idempotency**: Running ingestion twice should not create duplicate records (upsert semantics)
- **Resumability**: If embedding generation fails midway, it should resume from where it stopped
- **Observability**: Structured logging with progress metrics at each stage
- **Performance**: Full ingestion pipeline completes in < 30 minutes

## Technical Design

### Parser Interface

```python
class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: Path) -> list[CodeRecord]:
        """Parse an XML file and return structured code records."""
        pass

    @abstractmethod
    def validate(self, records: list[CodeRecord]) -> ValidationResult:
        """Validate parsed records for completeness and consistency."""
        pass
```

### Data Flow

```
XML Files -> Parser -> CodeRecord[] -> DB Loader -> PostgreSQL
                                    -> Chunker -> Chunk[] -> Embedder -> (vector, payload)[] -> Qdrant Loader -> Qdrant
```

## Acceptance Criteria

- [ ] All 5 XML files parsed without errors
- [ ] 98,186 codes (within 1% tolerance) loaded into PostgreSQL `codes` table
- [ ] All codes have: code, description, chapter, section, category, is_billable populated
- [ ] Metadata JSONB contains includes and excludes notes where present in source
- [ ] ~130K chunks loaded into Qdrant `icd10cm_chunks` collection
- [ ] All Qdrant payload indexes created and functional
- [ ] Sample queries return relevant results (manual verification of 10 clinical terms)
- [ ] Ingestion CLI runs end-to-end without manual intervention
- [ ] Ingestion is idempotent (second run produces same result, no duplicates)
- [ ] Validation step confirms DB count matches Qdrant count (for tabular chunks)

## Test Plan

### Unit Tests
- Test each parser with sample XML fragments
- Test chunk generation templates
- Test validation logic

### Integration Tests
- Test full pipeline with a small subset of XML data
- Test PostgreSQL loading and retrieval
- Test Qdrant loading and similarity search
- Test idempotency (run twice, verify no duplicates)

### Validation Tests
- Verify specific known codes exist (e.g., A01.0, E11.9, J18.9, M54.5)
- Verify hierarchy relationships (parent_code chain)
- Verify billable flag accuracy against known billable codes
- Spot-check 20 randomly selected codes for description accuracy
