# Auto Code - Product Vision

## What Is Auto Code?

Auto Code is an intelligent medical coding assistant that uses Retrieval Augmented Generation (RAG) to help healthcare professionals find accurate ICD-10-CM diagnosis codes from natural-language clinical descriptions. Instead of manually searching through 74,000+ billable codes across 1,500+ pages of hierarchical tables, clinicians and medical coders describe a patient's condition in plain language and receive precise, contextually-validated code recommendations in seconds.

## The Problem

Medical coding is the process of translating clinical documentation (physician notes, lab results, diagnoses) into standardized codes used for insurance billing, epidemiological tracking, and healthcare analytics. ICD-10-CM is the standard code set for diagnosis coding in the United States.

**Why is medical coding hard?**

1. **Scale.** ICD-10-CM contains ~74,000 billable codes organized in a deep hierarchy across 21 chapters. No human memorizes them all.
2. **Specificity requirements.** Insurance claims require the most specific code possible. "Diabetes" is not enough -- the code must specify type (1 vs 2), complication (kidney, eye, nerve), laterality (left vs right), and encounter type (initial, subsequent, sequela).
3. **Complex rules.** Codes have mutual exclusion rules (Excludes1), co-occurrence rules (Code First, Use Additional Code), and hierarchical inheritance that must be followed to avoid claim denials.
4. **Terminology gap.** Physicians describe conditions in clinical language; ICD-10-CM uses its own terminology. A physician writes "sugar diabetes" -- the code is under "Type 2 diabetes mellitus." The alphabetic index bridges this gap but is itself massive.
5. **Annual updates.** ICD-10-CM is updated every October (and sometimes April), adding, revising, and deleting codes. Coders must stay current.
6. **Error consequences.** Incorrect codes lead to claim denials (revenue loss), overpayment recovery (compliance risk), and in extreme cases, fraud allegations.

**Current solutions are inadequate:**

- **Manual lookup.** Searching PDF/book indexes is slow (5-15 minutes per code) and error-prone.
- **Simple code search tools.** Keyword search on code descriptions misses synonyms and does not surface coding rules (excludes, code first). High miss rate for complex conditions.
- **Legacy encoder software.** Expensive per-seat licenses, outdated UIs, poor natural-language understanding. Most do keyword matching, not semantic understanding.
- **General AI chatbots.** LLMs like ChatGPT or Claude have ICD-10-CM codes in their training data but hallucinate codes, use outdated versions, and cannot be trusted for billing accuracy. No audit trail, no compliance posture.

## The Solution

Auto Code combines the accuracy of an authoritative ICD-10-CM database with the natural-language understanding of modern LLMs, using RAG to ensure every recommendation is grounded in the actual code set:

1. **The clinician describes the condition** in natural language: "62-year-old male with type 2 diabetes and chronic kidney disease, seen for initial encounter."

2. **The retrieval pipeline searches** the vectorized ICD-10-CM database using hybrid search (semantic + keyword) across descriptions, clinical context, and index entries. It returns the most relevant codes with their full context (excludes, includes, instructions).

3. **The LLM analyzes the retrieved codes** against the clinical description and produces a structured recommendation: primary code, additional codes, confidence score, reasoning, and any warnings (Excludes1 conflicts, Code First requirements).

4. **The output is programmatically validated**: every recommended code is verified to exist in the retrieved context (no hallucinated codes), format is validated, excludes conflicts are cross-checked, and billable status is confirmed.

5. **The clinician reviews, accepts, and exports** the recommendation. Feedback is captured for continuous improvement.

### Key Differentiators

| Capability | Auto Code | Manual Lookup | Legacy Encoders | General AI |
|---|---|---|---|---|
| Natural language input | Yes | No | Limited | Yes |
| Grounded in current ICD-10-CM | Yes (April 2026) | Yes | Yes (if updated) | No (training data) |
| Hallucination prevention | Yes (RAG + validation) | N/A | N/A | No |
| Coding rules surfaced | Yes (Excludes, Code First) | Manual | Some | Unreliable |
| Confidence scoring | Yes | N/A | No | No |
| Audit trail | Yes | No | Some | No |
| Speed | Seconds | Minutes | Seconds | Seconds |
| Multi-tenant / HIPAA | Yes | N/A | Varies | No |
| Per-encounter cost | Cents | Labor cost | License fee | API cost |

## Who Is It For?

### Primary Users

**Medical Coders** - Certified professionals (CPC, CCS, RHIT, RHIA) who review clinical documentation and assign diagnosis codes. Auto Code accelerates their workflow and catches errors they might miss.

**Physician Practice Staff** - In smaller practices, coding is done by office staff who may not be certified coders. Auto Code provides expert-level guidance to non-specialists.

**Revenue Cycle Managers** - Responsible for claim submission accuracy and denial management. Auto Code reduces denial rates and accelerates the revenue cycle.

### Secondary Users

**Clinical Documentation Improvement (CDI) Specialists** - Review documentation for coding accuracy and completeness. Auto Code helps identify documentation gaps and suggest more specific codes.

**Health Information Management (HIM) Directors** - Oversee coding operations and compliance. Auto Code's audit trail and analytics support compliance monitoring.

## Design Principles

1. **Accuracy over speed.** A fast wrong code is worse than a slow correct one. Every recommendation must be grounded in the actual ICD-10-CM data. When uncertain, surface the uncertainty rather than guessing.

2. **Transparency.** Users must understand WHY a code was recommended. Show the reasoning, the source chunks, the confidence level, and any warnings. Never be a black box.

3. **Safety through constraints.** The LLM is a reasoning engine, not a code database. It sees only retrieved context and cannot access its training data for codes. Programmatic validation catches any leakage.

4. **Clinical workflow fit.** Coding happens in the context of patient encounters. The UI must support multi-code sessions, quick lookups, and export to existing workflow tools (CSV, PDF, clipboard).

5. **Compliance by design.** HIPAA compliance is not an afterthought. PHI stays on controlled infrastructure. Audit logs capture every action. Multi-tenant isolation prevents data leakage.

6. **Continuous improvement.** User feedback (corrections, ratings) feeds back into retrieval tuning, prompt refinement, and eventually model fine-tuning. The system gets better with use.

## Success Metrics

| Metric | Target | Measurement |
|---|---|---|
| Code recommendation accuracy (correct code in top-3) | > 95% | Measured against certified coder gold standard |
| Hallucination rate (recommended code not in ICD-10-CM) | < 0.1% | Programmatic validation logs |
| Time to code (from description input to accepted code) | < 30 seconds | Session duration analytics |
| User satisfaction (feedback rating) | > 4.5/5 | In-app feedback |
| Claim denial rate reduction | > 20% vs baseline | Customer-reported (post-launch) |
| System uptime | > 99.5% | Infrastructure monitoring |

## What Auto Code Is Not

- **Not a replacement for certified coders.** Auto Code is an assistant that suggests codes. A qualified human must review and accept every recommendation. The system explicitly positions itself as a decision-support tool, not an autonomous coding engine.
- **Not a clinical documentation system.** Auto Code does not generate or modify clinical notes. It takes existing documentation as input.
- **Not a billing/claims system.** Auto Code produces code recommendations. Claim submission, payment tracking, and denial management are handled by existing practice management software.
- **Not a general-purpose AI assistant.** Auto Code is purpose-built for ICD-10-CM coding. It does not answer general medical questions, provide clinical advice, or perform tasks outside its scope.
