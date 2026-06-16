// =============================================================================
// Authentication utilities -- Azure AD OIDC + JWT token management
// =============================================================================

const TOKEN_KEY = "autocode_access_token";
const REFRESH_KEY = "autocode_refresh_token";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

// ---- Token helpers ----------------------------------------------------------

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export function isAuthenticated(): boolean {
  const token = getAccessToken();
  if (!token) return false;

  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    const now = Math.floor(Date.now() / 1000);
    return payload.exp > now;
  } catch {
    return false;
  }
}

export function getCurrentUser(): {
  sub: string;
  email: string;
  name: string;
  tenant_id: string;
  role: string;
} | null {
  const token = getAccessToken();
  if (!token) return null;

  try {
    return JSON.parse(atob(token.split(".")[1]));
  } catch {
    return null;
  }
}

// ---- SSO Flow ---------------------------------------------------------------

export function redirectToSSO(tenantSlug: string): void {
  const redirectUri = `${window.location.origin}/callback`;
  window.location.href = `${API_BASE}/api/v1/auth/login?tenant=${encodeURIComponent(tenantSlug)}&redirect_uri=${encodeURIComponent(redirectUri)}`;
}

export async function handleSSOCallback(
  code: string,
): Promise<{ access_token: string; refresh_token: string }> {
  const redirectUri = `${window.location.origin}/callback`;
  const response = await fetch(`${API_BASE}/api/v1/auth/callback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, redirect_uri: redirectUri }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(
      error?.error?.message || "Authentication failed. Please try again.",
    );
  }

  const data = await response.json();
  setTokens(data.access_token, data.refresh_token);
  return data;
}

export async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  try {
    const response = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      clearTokens();
      return null;
    }

    const data = await response.json();
    setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  } catch {
    clearTokens();
    return null;
  }
}

export async function logout(): Promise<void> {
  const token = getAccessToken();
  if (token) {
    try {
      await fetch(`${API_BASE}/api/v1/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      // Swallow errors -- we clear locally regardless
    }
  }
  clearTokens();
  window.location.href = "/login";
}
