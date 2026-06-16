# User Journey Map: Medical Coder Workflow

## Initiative: INIT-001 Medical Coding Platform
## Persona: Clinical Medical Coder
## Last Updated: 2026-06-16

---

## Journey Overview

```
[Login] -> [Select Patient] -> [Enter Notes] -> [Review Codes] -> [Accept/Reject] -> [Export]
   |            |                    |                |                  |               |
   v            v                    v                v                  v               v
  SSO      Demographics        Clinical Text     AI Suggestions    Final Codes      Record
```

---

## Stage 1: Authentication & Login

**Actor:** Medical Coder
**Goal:** Securely access the platform

| Aspect | Detail |
|--------|--------|
| Action | Coder navigates to application URL, redirected to Azure AD SSO |
| System | OIDC authentication flow, JWT issued, tenant context resolved |
| Touchpoint | Login page with organization branding |
| Emotion | Neutral -- expects seamless SSO experience |
| Success | Coder lands on dashboard within 3 seconds of SSO completion |
| Pain Points | SSO misconfiguration, session expiry during active coding |

**Functional Requirements:**
- Azure AD OIDC integration
- JWT token with tenant_id and role claims
- Session persistence across browser tabs
- Automatic token refresh

---

## Stage 2: Select Patient or Enter Demographics

**Actor:** Medical Coder
**Goal:** Establish the patient context for the coding session

| Aspect | Detail |
|--------|--------|
| Action | Coder enters patient demographics (name, DOB, MRN) or selects from recent list |
| System | Creates or retrieves coding session, associates with patient context |
| Touchpoint | Patient selection panel / demographics form |
| Emotion | Task-oriented -- wants to move quickly to coding |
| Success | Patient context established, coding session created |
| Pain Points | Duplicate patient entries, required fields slowing workflow |

**Functional Requirements:**
- Patient demographics form (name, DOB, MRN, gender)
- Recent patients list for quick selection
- Session creation with patient association
- Optional EMR patient lookup integration

---

## Stage 3: Enter Clinical Notes

**Actor:** Medical Coder
**Goal:** Input the clinical narrative to be coded

| Aspect | Detail |
|--------|--------|
| Action | Coder types or pastes clinical notes into a large text input area |
| System | Text input captured, displayed in a social-media-post-like card format |
| Touchpoint | Clinical notes input area (rich text, expandable) |
| Emotion | Focused -- the core of their work begins here |
| Success | Clinical text submitted, AI analysis initiated with visible streaming indicator |
| Pain Points | Large notes hard to review, no spell-check, unclear what detail level is needed |

**Functional Requirements:**
- Large, resizable text input area
- Character/word count display
- Submit button initiating SSE streaming connection
- Loading/streaming state indicator
- Ability to edit and resubmit

---

## Stage 4: System Retrieves and Suggests Codes

**Actor:** System (AI)
**Goal:** Analyze clinical text and return relevant ICD-10-CM codes

| Aspect | Detail |
|--------|--------|
| Action | System processes clinical notes through RAG pipeline |
| System | Hybrid retrieval, cross-encoder reranking, LLM analysis, post-validation |
| Touchpoint | Streaming results display -- codes appear progressively |
| Emotion | Anticipation -- coder watches results stream in |
| Success | Relevant codes returned with confidence scores and source references |
| Pain Points | Slow response, irrelevant suggestions, missing obvious codes |

**System Processing Steps:**
1. Clinical text chunked and embedded
2. Hybrid retrieval: dense vector search + sparse keyword matching
3. Metadata filtering by code type and chapter
4. Cross-encoder reranking of candidate codes
5. Hierarchy expansion (parent/child codes, excludes notes)
6. LLM analysis with negative prompting for precision
7. Post-LLM validation against PostgreSQL code database
8. Results streamed via SSE to client

---

## Stage 5: Review, Accept, or Reject Codes

**Actor:** Medical Coder
**Goal:** Validate AI suggestions and finalize the code set

| Aspect | Detail |
|--------|--------|
| Action | Coder reviews each suggested code card, accepts correct codes, rejects incorrect ones |
| System | Code cards display: code, description, confidence, hierarchy, excludes, source reference |
| Touchpoint | Interactive code cards with accept/reject actions |
| Emotion | Critical evaluation -- this is where clinical expertise matters |
| Success | All relevant codes accepted, irrelevant ones rejected, final set is accurate |
| Pain Points | Too many suggestions to review, missing context for decision-making, no way to add manual codes |

**Functional Requirements:**
- Code cards with full detail (code, description, confidence score)
- Hierarchy breadcrumb (chapter > section > category > code)
- Excludes1 and Excludes2 notes display
- Includes notes and code-first/use-additional annotations
- Accept/reject toggle per code
- Manual code search and addition
- Confidence threshold filtering

---

## Stage 6: Export Coded Record

**Actor:** Medical Coder
**Goal:** Generate the final coded record for downstream systems

| Aspect | Detail |
|--------|--------|
| Action | Coder selects export format and generates the coded record |
| System | Generates document with patient demographics, clinical notes, and coding output |
| Touchpoint | Export dialog with format selection |
| Emotion | Completion -- task is wrapping up |
| Success | Clean, accurate export ready for billing/EMR system |
| Pain Points | Missing fields in export, format incompatibility with downstream system |

**Export Formats:**
- **PDF** -- Formatted report with header, clinical notes summary, and code table
- **CSV** -- Flat file with code, description, confidence, and status columns
- **JSON** -- Structured data for API consumers
- **HL7 FHIR** -- Standard healthcare interoperability format

**Export Content:**
1. Patient demographics header
2. Encounter/session metadata
3. Clinical notes (original input)
4. Coding output table (accepted codes with descriptions and references)
5. Audit trail (timestamp, coder, AI confidence scores)

---

## Edge Cases & Alternative Flows

### No Codes Found
- System returns empty results with suggestion to refine clinical notes
- Coder can access code browser for manual lookup

### Low Confidence Results
- Codes below confidence threshold shown in a separate "Review Needed" section
- Visual indicator (amber/red) for low-confidence suggestions

### Session Recovery
- Auto-save of clinical notes and coding decisions
- Session resumption after browser close or network interruption

### Multi-Encounter Coding
- Coder can create multiple coding sessions per patient
- Session history accessible from patient context

---

## Metrics & Instrumentation

| Metric | Collection Point | Purpose |
|--------|-----------------|---------|
| Time to first code suggestion | Stage 4 start to first SSE event | Latency monitoring |
| Codes accepted vs rejected ratio | Stage 5 actions | AI accuracy feedback loop |
| Manual codes added | Stage 5 manual search | Gap identification |
| Export format preference | Stage 6 format selection | Feature prioritization |
| Session duration | Stage 2 creation to Stage 6 export | Workflow efficiency |
| Resubmission rate | Stage 3 edit-and-resubmit | Input quality signal |
