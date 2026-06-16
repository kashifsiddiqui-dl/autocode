# FEAT-005: Export

## Status: Not Started
## Priority: P1
## Release: R2 Web Interface
## Owner: TBD
## Estimated Effort: 1 week
## Depends On: FEAT-003, FEAT-004

---

## Summary

Enable export of completed coding sessions in PDF, CSV, JSON, and HL7 FHIR formats. Each export includes a patient demographics header, treatment/encounter details, the original clinical notes, and the full coding output with references and audit trail.

## Problem Statement

Coded medical records must be transmitted to billing systems, EMRs, and compliance archives. Each downstream system expects a different format. The export must be complete, accurate, and include all information needed for audit compliance -- including which codes were AI-suggested vs manually added, and the AI's confidence scores.

## Functional Requirements

### FR-1: Export API Endpoint

```
POST /api/v1/coding/sessions/{session_id}/export
Content-Type: application/json

Request Body:
{
  "format": "pdf" | "csv" | "json" | "hl7_fhir",
  "options": {
    "include_rejected": false,         // Include rejected codes in export
    "include_reasoning": true,         // Include AI reasoning text
    "include_confidence": true,        // Include confidence scores
    "include_audit_trail": true,       // Include timestamps and user actions
    "include_clinical_notes": true     // Include original clinical text
  }
}

Response:
- PDF: application/pdf binary stream
- CSV: text/csv with Content-Disposition header
- JSON: application/json structured document
- HL7 FHIR: application/fhir+json
```

### FR-2: Export Content Structure

All export formats include these sections:

**1. Header / Patient Demographics**
- Patient name
- Date of birth
- Medical record number (MRN)
- Gender
- Encounter date (session creation date)
- Exporting organization (tenant name)
- Export date and time

**2. Treatment Details / Clinical Notes**
- Original clinical text as submitted
- Session ID for reference
- Coding standard used (e.g., ICD-10-CM 2026)

**3. Coding Output**

For each accepted code (and optionally rejected codes):

| Field | Description |
|-------|-------------|
| Code | ICD-10-CM code |
| Description | Short description |
| Status | Accepted / Rejected / Suggested |
| Confidence | AI confidence score (0.0-1.0) |
| Source | AI-suggested / Manually added |
| Reasoning | AI's explanation for the code (optional) |
| Hierarchy | Chapter > Section > Category path |
| Is Billable | Whether the code is billable |

**4. Audit Trail**
- Session created: timestamp, user
- Analysis completed: timestamp, duration
- Codes reviewed: timestamp, user, action (accept/reject) per code
- Export generated: timestamp, user, format

### FR-3: PDF Export

- Professional layout suitable for medical records
- Organization logo placeholder in header
- Patient demographics in a bordered header section
- Clinical notes in a readable text block
- Coding output as a formatted table
- Color coding: accepted codes in green rows, rejected in red (if included)
- Footer with page numbers and export timestamp
- Generated using a Python PDF library (e.g., ReportLab or WeasyPrint)

### FR-4: CSV Export

```csv
"Export Date","2026-06-16T14:30:00Z"
"Patient Name","John Doe"
"Date of Birth","1965-03-15"
"MRN","MRN-12345"
"Gender","Male"
"Encounter Date","2026-06-16"
"Standard","ICD-10-CM 2026"

"Code","Description","Status","Confidence","Source","Billable","Reasoning"
"E11.9","Type 2 diabetes mellitus without complications","Accepted","0.95","AI-suggested","Yes","Clinical notes mention..."
"I10","Essential (primary) hypertension","Accepted","0.92","AI-suggested","Yes","Patient presents with..."
```

- UTF-8 encoding with BOM for Excel compatibility
- Header rows with patient demographics
- Blank row separator
- Data rows with coding output
- Properly escaped fields (RFC 4180 compliant)

### FR-5: JSON Export

```json
{
  "export_version": "1.0",
  "export_date": "2026-06-16T14:30:00Z",
  "session_id": "uuid",
  "standard": {
    "name": "ICD-10-CM",
    "version": "2026",
    "effective_date": "2026-04-01"
  },
  "patient": {
    "name": "John Doe",
    "date_of_birth": "1965-03-15",
    "mrn": "MRN-12345",
    "gender": "male"
  },
  "encounter": {
    "date": "2026-06-16",
    "clinical_notes": "Patient presents with...",
    "organization": "Example Health System"
  },
  "codes": [
    {
      "code": "E11.9",
      "description": "Type 2 diabetes mellitus without complications",
      "status": "accepted",
      "confidence": 0.95,
      "source": "ai_suggested",
      "is_billable": true,
      "reasoning": "Clinical notes mention...",
      "hierarchy": {
        "chapter": "4",
        "chapter_description": "Endocrine, nutritional and metabolic diseases",
        "section": "E08-E13",
        "section_description": "Diabetes mellitus",
        "category": "E11"
      }
    }
  ],
  "audit_trail": [
    {"action": "session_created", "timestamp": "...", "user": "..."},
    {"action": "analysis_completed", "timestamp": "...", "duration_ms": 3200},
    {"action": "code_accepted", "timestamp": "...", "user": "...", "code": "E11.9"},
    {"action": "export_generated", "timestamp": "...", "user": "...", "format": "json"}
  ]
}
```

### FR-6: HL7 FHIR Export

Generate a FHIR R4 Bundle containing:

- **Patient** resource with demographics
- **Encounter** resource linked to the patient
- **Condition** resources for each accepted code (linked to encounter and patient)
- **DiagnosticReport** resource containing the clinical notes

Each Condition resource:
```json
{
  "resourceType": "Condition",
  "code": {
    "coding": [
      {
        "system": "http://hl7.org/fhir/sid/icd-10-cm",
        "code": "E11.9",
        "display": "Type 2 diabetes mellitus without complications"
      }
    ]
  },
  "subject": {"reference": "Patient/uuid"},
  "encounter": {"reference": "Encounter/uuid"},
  "recordedDate": "2026-06-16"
}
```

### FR-7: Export UI

- Export button on session detail page (enabled when session has accepted codes)
- Format selection dropdown (PDF, CSV, JSON, HL7 FHIR)
- Options checkboxes (include rejected, include reasoning, etc.)
- Download triggered in browser (file download, not navigation)
- Loading state during export generation
- Success toast with file name

## Non-Functional Requirements

- **Performance**: Export generation < 3 seconds for sessions with up to 25 codes
- **File size**: PDF < 1MB for typical sessions
- **Compliance**: HL7 FHIR output validates against FHIR R4 spec
- **Encoding**: All text exports in UTF-8

## Acceptance Criteria

- [ ] Export endpoint accepts session_id and format parameter
- [ ] PDF export generates a professionally formatted document with all sections
- [ ] CSV export is RFC 4180 compliant and opens correctly in Excel
- [ ] JSON export produces valid JSON matching the specified schema
- [ ] HL7 FHIR export produces a valid FHIR R4 Bundle
- [ ] Patient demographics appear in all export formats
- [ ] Only accepted codes are included by default (rejected codes optional)
- [ ] Audit trail is included when option is enabled
- [ ] Export UI allows format selection and option configuration
- [ ] File downloads work in all supported browsers
- [ ] Export of a session with no accepted codes returns an appropriate error

## Test Plan

### Unit Tests
- Test each export format generator with known input data
- Test CSV escaping edge cases (commas, quotes, newlines in fields)
- Test JSON schema validation
- Test FHIR Bundle structure validation

### Integration Tests
- Test full export flow: create session -> accept codes -> export -> validate output
- Test each format with a representative coding session
- Test export options (include/exclude rejected, reasoning, etc.)

### Validation Tests
- Validate PDF renders correctly (visual inspection + text extraction)
- Validate CSV opens in Excel without data corruption
- Validate JSON against JSON Schema
- Validate HL7 FHIR against FHIR R4 validator
