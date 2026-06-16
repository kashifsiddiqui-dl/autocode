// =============================================================================
// API client -- typed fetch wrapper with SSE streaming support
// =============================================================================

import {
  type ApiError,
  type CategoryNode,
  type ChapterNode,
  type CodeDetail,
  type CodeSearchResult,
  type CodingRequest,
  type CodingSession,
  type CodingSessionList,
  type CodingStandardInfo,
  type ExportRequest,
  type ExportResponse,
  type HealthResponse,
  type PaginatedResponse,
  type Patient,
  type PatientCreate,
  type SectionNode,
  type SSECodeEvent,
  type SSECompleteEvent,
  type SSEEvent,
  type SSESessionEvent,
  type SSEStageEvent,
  type User,
} from "./types";
import { getAccessToken, refreshAccessToken, clearTokens } from "./auth";

// ---- Error classes ----------------------------------------------------------

export class ApiRequestError extends Error {
  status: number;
  code: string;
  details?: unknown[];

  constructor(status: number, body: ApiError) {
    super(body.error.message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = body.error.code;
    this.details = body.error.details;
  }
}

// ---- API Client -------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function getAuthHeaders(): Promise<Record<string, string>> {
  let token = getAccessToken();

  if (!token) {
    token = await refreshAccessToken();
  }

  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.status === 401) {
    const newToken = await refreshAccessToken();
    if (!newToken) {
      clearTokens();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new ApiRequestError(401, {
        error: { code: "AUTHENTICATION_ERROR", message: "Session expired" },
      });
    }
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({
      error: { code: "UNKNOWN_ERROR", message: response.statusText },
    }));
    throw new ApiRequestError(response.status, body as ApiError);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

export const apiClient = {
  // ---- Generic methods ------------------------------------------------------

  async get<T>(path: string, params?: Record<string, string>): Promise<T> {
    const url = new URL(`${API_BASE}${path}`, window.location.origin);
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== "") url.searchParams.set(k, v);
      });
    }
    const headers = await getAuthHeaders();
    const response = await fetch(url.toString(), {
      headers: { ...headers, Accept: "application/json" },
    });
    return handleResponse<T>(response);
  },

  async post<T>(path: string, body?: unknown): Promise<T> {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(response);
  },

  async patch<T>(path: string, body: unknown): Promise<T> {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE}${path}`, {
      method: "PATCH",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return handleResponse<T>(response);
  },

  async delete<T = void>(path: string): Promise<T> {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_BASE}${path}`, {
      method: "DELETE",
      headers,
    });
    return handleResponse<T>(response);
  },

  // ---- Coding Analysis (SSE) ------------------------------------------------

  async analyzeCoding(
    request: CodingRequest,
    onEvent: (event: SSEEvent) => void,
    onError?: (error: Error) => void,
  ): Promise<AbortController> {
    const controller = new AbortController();
    const headers = await getAuthHeaders();

    try {
      const response = await fetch(`${API_BASE}/api/v1/coding/analyze`, {
        method: "POST",
        headers: {
          ...headers,
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify(request),
        signal: controller.signal,
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({
          error: { code: "UNKNOWN_ERROR", message: response.statusText },
        }));
        throw new ApiRequestError(response.status, body as ApiError);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      const processStream = async () => {
        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            let currentEvent = "";
            let currentData = "";

            for (const line of lines) {
              if (line.startsWith("event: ")) {
                currentEvent = line.slice(7).trim();
              } else if (line.startsWith("data: ")) {
                currentData = line.slice(6).trim();
              } else if (line === "" && currentEvent && currentData) {
                try {
                  const parsed = JSON.parse(currentData);
                  switch (currentEvent) {
                    case "session":
                      onEvent({
                        event: "session",
                        data: parsed as SSESessionEvent,
                      });
                      break;
                    case "stage":
                      onEvent({
                        event: "stage",
                        data: parsed as SSEStageEvent,
                      });
                      break;
                    case "code":
                      onEvent({
                        event: "code",
                        data: parsed as SSECodeEvent,
                      });
                      break;
                    case "complete":
                      onEvent({
                        event: "complete",
                        data: parsed as SSECompleteEvent,
                      });
                      break;
                  }
                } catch {
                  // Skip malformed events
                }
                currentEvent = "";
                currentData = "";
              }
            }
          }
        } catch (err) {
          if ((err as Error).name !== "AbortError") {
            onError?.(err as Error);
          }
        }
      };

      processStream();
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        onError?.(err as Error);
      }
    }

    return controller;
  },

  // ---- Sessions -------------------------------------------------------------

  async getSessions(params?: {
    page?: string;
    per_page?: string;
    status?: string;
  }): Promise<PaginatedResponse<CodingSessionList>> {
    return this.get("/api/v1/coding/sessions", params);
  },

  async getSession(id: string): Promise<CodingSession> {
    return this.get(`/api/v1/coding/sessions/${id}`);
  },

  async updateSession(
    id: string,
    body: { status: string },
  ): Promise<CodingSession> {
    return this.patch(`/api/v1/coding/sessions/${id}`, body);
  },

  async deleteSession(id: string): Promise<void> {
    return this.delete(`/api/v1/coding/sessions/${id}`);
  },

  async updateResult(
    sessionId: string,
    resultId: string,
    body: { status: string },
  ): Promise<void> {
    return this.patch(
      `/api/v1/coding/sessions/${sessionId}/results/${resultId}`,
      body,
    );
  },

  // ---- Code Browser ---------------------------------------------------------

  async getChapters(): Promise<ChapterNode[]> {
    return this.get("/api/v1/codes/chapters");
  },

  async getSections(chapter: string): Promise<SectionNode[]> {
    return this.get(`/api/v1/codes/chapters/${chapter}/sections`);
  },

  async getCodes(params: { parent: string }): Promise<CategoryNode[]> {
    return this.get("/api/v1/codes/browse", params);
  },

  async getCode(code: string): Promise<CodeDetail> {
    return this.get(`/api/v1/codes/${code}`);
  },

  async getCodeHierarchy(code: string): Promise<CodeDetail> {
    return this.get(`/api/v1/codes/${code}`);
  },

  async searchCodes(
    q: string,
    limit: number = 20,
  ): Promise<CodeSearchResult[]> {
    return this.get("/api/v1/codes/search", {
      q,
      limit: limit.toString(),
    });
  },

  // ---- Patients -------------------------------------------------------------

  async getPatients(params?: {
    page?: string;
    per_page?: string;
  }): Promise<PaginatedResponse<Patient>> {
    return this.get("/api/v1/patients", params);
  },

  async createPatient(data: PatientCreate): Promise<Patient> {
    return this.post("/api/v1/patients", data);
  },

  // ---- Export ----------------------------------------------------------------

  async createExport(
    sessionId: string,
    request: ExportRequest,
  ): Promise<ExportResponse> {
    return this.post(
      `/api/v1/coding/sessions/${sessionId}/export`,
      request,
    );
  },

  async downloadExport(sessionId: string, request: ExportRequest): Promise<Blob> {
    const headers = await getAuthHeaders();
    const response = await fetch(
      `${API_BASE}/api/v1/coding/sessions/${sessionId}/export`,
      {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify(request),
      },
    );

    if (!response.ok) {
      const body = await response.json().catch(() => ({
        error: { code: "EXPORT_ERROR", message: "Export failed" },
      }));
      throw new ApiRequestError(response.status, body as ApiError);
    }

    return response.blob();
  },

  // ---- Users ----------------------------------------------------------------

  async getUsers(): Promise<User[]> {
    return this.get("/api/v1/users");
  },

  async createUser(data: {
    email: string;
    name: string;
    role: string;
  }): Promise<User> {
    return this.post("/api/v1/users", data);
  },

  async updateUser(id: string, body: { role: string }): Promise<User> {
    return this.patch(`/api/v1/users/${id}`, body);
  },

  async deleteUser(id: string): Promise<void> {
    return this.delete(`/api/v1/users/${id}`);
  },

  // ---- Standards ------------------------------------------------------------

  async getStandards(): Promise<CodingStandardInfo[]> {
    return this.get("/api/v1/standards");
  },

  // ---- Health ---------------------------------------------------------------

  async getHealth(): Promise<HealthResponse> {
    return this.get("/api/v1/health");
  },
};
