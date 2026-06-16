# Auto Code Glossary

Terminology reference for medical coding, healthcare IT, and project-specific concepts used throughout the Auto Code codebase and documentation.

## Medical Coding Terms

### ICD-10-CM
**International Classification of Diseases, 10th Revision, Clinical Modification.** The US standard for reporting medical diagnoses on insurance claims. Maintained by the CDC's National Center for Health Statistics (NCHS). Updated annually (October 1) with occasional mid-year updates (April 1). Current version: April 1, 2026.

### Billable Code
A code specific enough to be accepted on an insurance claim. Billable codes are leaf nodes in the ICD-10-CM hierarchy (no further subdivisions exist). Identified by `is_billable=1` in the order file. Example: `E11.22` (Type 2 diabetes mellitus with diabetic chronic kidney disease) is billable; `E11` (Type 2 diabetes mellitus) is not.

### Category Code
A 3-character code that represents the top level of a condition grouping within a section. Category codes are never billable -- they require further specificity. Example: `A00` (Cholera), `E11` (Type 2 diabetes mellitus), `S72` (Fracture of femur).

### Subcategory Code
A 4- or 5-character refinement of a category code, adding clinical specificity. Some subcategories are billable; others require further extension. Example: `E11.2` (Type 2 diabetes mellitus with kidney complications) is a subcategory of `E11`.

### 7th Character Extension
A character appended to codes (with placeholder `X` if the code has fewer than 6 characters) that provides additional clinical detail. Common uses:
- **Laterality:** `1` = right, `2` = left, `3` = bilateral
- **Encounter type:** `A` = initial encounter, `D` = subsequent encounter, `S` = sequela
- **Fracture healing:** `A` = initial closed, `B` = initial open type I/II, `K` = subsequent with nonunion, etc.
Example: `S72.001A` = Fracture of unspecified part of neck of right femur, initial encounter for closed fracture.

### Placeholder X
The letter `X` used as a placeholder in codes that require a 7th character but have fewer than 6 characters. The `X` fills positions to reach the required length. Example: `T39.1X1A` -- the `X` fills the 5th position so the 7th character (`A` = initial encounter) can be placed correctly.

### Excludes1
A "NOT CODED HERE" note. Indicates that the condition described by the Excludes1 note and the code where the note appears are **mutually exclusive** and should **never** be coded together. If a patient has both conditions, only one code should be used (determined by sequencing rules). Example: Under `E10` (Type 1 diabetes), Excludes1 includes `E11` (Type 2 diabetes) -- a patient cannot have both Type 1 and Type 2.

### Excludes2
A "NOT INCLUDED HERE" note. Indicates that the condition in the Excludes2 note is not part of the condition represented by the code, but a **patient may have both conditions simultaneously**. Both codes can appear on the same claim. Example: Under `J44` (COPD), Excludes2 includes `J45` (Asthma) -- a patient can have both COPD and asthma coded.

### Code First
An instructional note indicating that the underlying condition (etiology) must be sequenced (listed) before the manifestation code. The code with the "Code First" note is a manifestation and cannot be the primary/first-listed diagnosis. Example: `H36` (Retinal disorders in diseases classified elsewhere) has "Code First underlying disease."

### Use Additional Code
An instructional note indicating that a secondary code should be added to provide more complete information. The code with this note is sequenced first, followed by the additional code. Example: `E11` has "Use additional code to identify control using insulin (Z79.4)."

### Code Also
An instructional note indicating that two codes may be needed to fully describe a condition. Unlike "Use Additional Code," sequencing depends on the clinical circumstances. Example: `J96.0` (Acute respiratory failure) has "Code also any associated conditions."

### Inclusion Terms
A list of conditions, synonyms, or alternate descriptions that are classified to a particular code. These terms are not exhaustive but indicate the scope of the code. Example: Under `A00.0` (Cholera due to Vibrio cholerae 01, biovar cholerae), inclusion terms include "Classical cholera."

### Tabular List
The main body of the ICD-10-CM classification, organized numerically by code. Contains all codes with their descriptions, includes/excludes notes, and coding instructions. Source file: `icd10c-tabular-April-1-2026.xml`.

### Alphabetic Index
A cross-reference index that maps natural-language condition terms to their corresponding tabular list codes. Entry point for code lookup when you know the condition name but not the code. Source file: `icd10cm-index-April-1-2026-XML.xml`.

### Table of Drugs and Chemicals
A specialized index mapping substances to poisoning, adverse effect, and underdosing codes with columns for intent (accidental, intentional self-harm, assault, undetermined). Source file: `icd10cm-drug-April-1-2026-XML.xml`.

### Neoplasm Table
A specialized index mapping anatomical sites to neoplasm codes with columns for behavior (malignant primary, malignant secondary, carcinoma in situ, benign, uncertain behavior, unspecified behavior). Source file: `icd10cm-neoplasm-April-1-2026-XML.xml`.

### External Cause Index (E-Index)
An alphabetic index for external causes of morbidity (V00-Y99). Maps descriptions of how injuries/conditions occurred to the appropriate external cause code. Source file: `icd10cm-eindex-April-1-2026-XML.xml`.

### Addenda
Annual update documents listing codes that have been added, revised, or deleted since the previous version. Source files: `icd10cm-*-addenda-April-1-2026.pdf`.

### Coding Guidelines
The official ICD-10-CM Official Guidelines for Coding and Reporting, published by CMS and NCHS. Provides rules for code selection, sequencing, and application. Source file: `ICD-10-CM April 1 2026 Guidelines Final.pdf`.

## Healthcare IT Terms

### PHI (Protected Health Information)
Any individually identifiable health information held or transmitted by a covered entity or its business associates. Includes: names, dates, phone numbers, email addresses, SSNs, medical record numbers, health plan beneficiary numbers, device identifiers, biometric identifiers, photographs, and any other unique identifying number or code. Under HIPAA, PHI must be safeguarded with administrative, physical, and technical controls.

### HIPAA (Health Insurance Portability and Accountability Act)
US federal law (1996) that establishes national standards for the protection of electronic health information. Key rules: Privacy Rule (who can access PHI), Security Rule (how to protect ePHI), Breach Notification Rule (what to do when PHI is exposed).

### BAA (Business Associate Agreement)
A contract between a HIPAA-covered entity (e.g., a hospital) and a business associate (e.g., Auto Code) that establishes the permitted uses and disclosures of PHI. Required before any PHI is shared. Auto Code must have a BAA with each customer organization.

### RLS (Row-Level Security)
A database access control mechanism that restricts which rows a user/tenant can access based on their identity. In Auto Code, every database table with tenant data includes a `tenant_id` column, and queries are automatically filtered to the authenticated user's tenant.

### SSO (Single Sign-On)
An authentication scheme that allows users to log in once with a single set of credentials (typically their organizational credentials) and gain access to multiple applications without re-authenticating. Auto Code uses Azure AD OIDC for SSO.

### OIDC (OpenID Connect)
An authentication layer built on top of OAuth 2.0. Provides a standardized way for applications to verify user identity via an identity provider (e.g., Azure AD) and obtain basic profile information. Simpler than SAML for modern web applications.

### EMR / EHR (Electronic Medical Record / Electronic Health Record)
Software systems used by healthcare providers to maintain patient medical records digitally. Common EMR systems: Epic, Cerner (Oracle Health), MEDITECH, Allscripts. Auto Code may integrate with EMR systems in future phases for direct code insertion.

### FHIR (Fast Healthcare Interoperability Resources)
A standard for exchanging healthcare information electronically, developed by HL7. Uses RESTful APIs with JSON/XML resources. Relevant for future EMR integrations.

## AI / ML Terms

### RAG (Retrieval Augmented Generation)
An AI architecture pattern where a language model's generation is augmented with information retrieved from an external knowledge base (in our case, the Qdrant vector database of ICD-10-CM codes). The model generates responses grounded in retrieved facts rather than relying solely on its training data. This is the core architecture of Auto Code.

### Vector Embedding
A fixed-size numerical representation (array of floats) of text that captures semantic meaning. Similar texts produce similar embeddings (close in vector space). Auto Code uses embeddings to find ICD-10-CM codes semantically similar to a user's clinical description.

### Named Vectors
A Qdrant feature allowing multiple embedding representations to be stored on the same data point. Auto Code stores `description` (OpenAI 1024d) and `clinical_context` (PubMedBERT 768d) as separate named vectors per code chunk.

### Sparse Vectors
Vector representations where most values are zero, storing only non-zero entries as (index, value) pairs. Used for BM25-style keyword matching in Qdrant alongside dense semantic vectors for hybrid search.

### Hybrid Search
A retrieval strategy combining dense semantic search (embedding similarity) with sparse keyword search (BM25 term matching). Results from both are fused (typically via Reciprocal Rank Fusion) to produce a final ranking that captures both semantic meaning and exact term matches.

### Reciprocal Rank Fusion (RRF)
A rank aggregation method that combines multiple ranked lists by summing reciprocal ranks: `score(d) = sum(1 / (k + rank_i(d)))` across all lists. Simple, effective, and parameter-light (only `k`, typically 60). Used to fuse dense and sparse search results.

### Negative Prompting
A prompt engineering technique where the system prompt explicitly tells the LLM what NOT to do. In Auto Code, the LLM is instructed to NEVER generate codes from its training data and to ONLY use codes present in the retrieved context. This prevents hallucinated codes.

### Hallucination
When an LLM generates information that appears plausible but is factually incorrect or fabricated. In medical coding, a hallucinated code could be a real code used in the wrong context, an outdated code, or a completely fabricated code. Hallucination prevention is a critical safety requirement.

### Temperature
A parameter controlling the randomness of LLM output. `temperature=0.0` produces the most deterministic output (always selecting the highest-probability token). Auto Code defaults to `temperature=0.0` because medical coding requires precision and reproducibility, not creativity.

## Project-Specific Terms

### Chunk
A single unit of data stored in the vector database. In Auto Code, each chunk represents one ICD-10-CM code entry (billable code, category, index entry, drug entry, or neoplasm entry) with its full inherited context. See ADR-002.

### Tenant
An organization (hospital, health system, billing company) using Auto Code. Each tenant has isolated data, configuration, and user accounts. Tenant context is established at authentication and enforced via RLS on every database query.

### Coding Session
A user interaction where a clinician submits a clinical description and receives ICD-10-CM code recommendations. Each session is logged with the query, retrieved chunks, LLM response, and user feedback for audit and quality improvement.

### Provider (LLM context)
An LLM API service (Anthropic, OpenAI) abstracted behind the `LLMProvider` interface. Not to be confused with healthcare provider (clinician/hospital). Context should make the meaning clear.
