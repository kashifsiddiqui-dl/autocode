// =============================================================================
// TypeScript interfaces matching backend schemas
// =============================================================================

// ---- Patients ---------------------------------------------------------------

export interface Patient {
  id: string;
  name: string;
  dob: string;
  mrn: string;
  gender: string;
  tenant_id: string;
  created_at: string;
  updated_at: string;
}

export interface PatientCreate {
  name: string;
  dob: string;
  mrn: string;
  gender: string;
}

// ---- Coding -----------------------------------------------------------------

export interface CodingOptions {
  max_results?: number;
  min_confidence?: number;
  billable_only?: boolean;
  chapter_filter?: string[];
  standard?: CodingStandard;
  version?: string;
}

export interface CodingRequest {
  clinical_text: string;
  session_id?: string;
  patient?: {
    name?: string;
    dob?: string;
    mrn?: string;
    gender?: string;
  };
  options?: CodingOptions;
}

export interface CodeExcludes {
  excludes1?: string[];
  excludes2?: string[];
}

export interface CodeAnnotations {
  code_first?: string;
  use_additional?: string;
  includes?: string[];
}

export interface CodeHierarchy {
  chapter: string;
  chapter_description: string;
  section: string;
  section_description: string;
  category: string;
  category_description?: string;
}

export interface CodeDetail {
  code: string;
  short_description: string;
  long_description: string;
  is_billable: boolean;
  hierarchy: CodeHierarchy;
  excludes?: CodeExcludes;
  annotations?: CodeAnnotations;
  seventh_character?: SeventhCharacterOption[];
  parent_code?: string;
  child_codes?: string[];
  sibling_codes?: string[];
}

export interface SeventhCharacterOption {
  character: string;
  description: string;
}

export type ResultStatus = "suggested" | "accepted" | "rejected";

export interface CodingResult {
  id: string;
  code: string;
  description: string;
  confidence: number;
  reasoning: string;
  is_billable: boolean;
  hierarchy: CodeHierarchy;
  excludes?: CodeExcludes;
  annotations?: CodeAnnotations;
  seventh_character?: SeventhCharacterOption[];
  status: ResultStatus;
  source: "ai_suggested" | "manually_added";
}

export type SessionStatus = "draft" | "in_review" | "completed";

export interface CodingSession {
  id: string;
  clinical_text: string;
  patient?: Patient;
  status: SessionStatus;
  results: CodingResult[];
  standard: CodingStandard;
  version: string;
  created_at: string;
  updated_at: string;
  duration_ms?: number;
  total_codes?: number;
  user_id: string;
  tenant_id: string;
}

export interface CodingSessionList {
  id: string;
  patient_name?: string;
  status: SessionStatus;
  code_count: number;
  standard: CodingStandard;
  created_at: string;
  updated_at: string;
}

// ---- Export -----------------------------------------------------------------

export type ExportFormat = "pdf" | "csv" | "json" | "hl7_fhir";

export interface ExportOptions {
  include_rejected?: boolean;
  include_reasoning?: boolean;
  include_confidence?: boolean;
  include_audit_trail?: boolean;
  include_clinical_notes?: boolean;
}

export interface ExportRequest {
  format: ExportFormat;
  options?: ExportOptions;
}

export interface ExportResponse {
  download_url: string;
  filename: string;
  format: ExportFormat;
  size_bytes: number;
}

// ---- Users & Tenants --------------------------------------------------------

export type UserRole = "admin" | "coder" | "viewer";

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  tenant_id: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  azure_tenant_id: string;
  default_standard: CodingStandard;
  is_active: boolean;
  created_at: string;
}

// ---- Coding Standards -------------------------------------------------------

export type CodingStandard = "icd10cm" | "icd10pcs" | "cpt" | "hcpcs";

export interface CodingStandardInfo {
  name: string;
  code: CodingStandard;
  version: string;
  effective_date: string;
  is_active: boolean;
}

// ---- Code Browser -----------------------------------------------------------

export interface ChapterNode {
  chapter: string;
  code_range: string;
  description: string;
  section_count: number;
}

export interface SectionNode {
  code_range: string;
  description: string;
  category_count: number;
}

export interface CategoryNode {
  code: string;
  description: string;
  code_count: number;
  is_billable: boolean;
}

export interface CodeSearchResult {
  code: string;
  description: string;
  chapter: string;
  is_billable: boolean;
  relevance_score: number;
  hierarchy: CodeHierarchy;
}

// ---- Pagination -------------------------------------------------------------

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// ---- SSE Events -------------------------------------------------------------

export interface SSESessionEvent {
  session_id: string;
  status: "processing";
}

export interface SSEStageEvent {
  stage: "retrieval" | "reranking" | "analysis" | "validation";
  status: "started" | "completed";
  duration_ms?: number;
  candidates?: number;
  codes_validated?: number;
  codes_removed?: number;
}

export interface SSECodeEvent {
  code: string;
  description: string;
  confidence: number;
  reasoning: string;
  is_billable: boolean;
  hierarchy: CodeHierarchy;
  excludes?: CodeExcludes;
  annotations?: CodeAnnotations;
  seventh_character?: SeventhCharacterOption[];
}

export interface SSECompleteEvent {
  session_id: string;
  total_codes: number;
  duration_ms: number;
}

export type SSEEvent =
  | { event: "session"; data: SSESessionEvent }
  | { event: "stage"; data: SSEStageEvent }
  | { event: "code"; data: SSECodeEvent }
  | { event: "complete"; data: SSECompleteEvent };

// ---- API Errors -------------------------------------------------------------

export interface ApiErrorDetail {
  field: string;
  issue: string;
  [key: string]: unknown;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: ApiErrorDetail[];
  };
}

// ---- Health -----------------------------------------------------------------

export interface HealthResponse {
  status: string;
  services: {
    postgres: string;
    qdrant: string;
    redis: string;
  };
}

// ---- LLM Provider -----------------------------------------------------------

export type LLMProvider = "anthropic" | "openai";
