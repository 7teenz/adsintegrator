import { clearAuth, getToken } from "@/lib/auth";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api/proxy";

interface RequestOptions extends RequestInit {
  token?: string;
  noAuth?: boolean;
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { token, noAuth, headers, ...rest } = options;
  const authToken = token || (!noAuth ? getToken() : null);
  const url = `${API_URL}${path}`;
  const isFormData = typeof FormData !== "undefined" && rest.body instanceof FormData;
  const baseHeaders = new Headers(headers ?? undefined);
  if (authToken) {
    baseHeaders.set("Authorization", `Bearer ${authToken}`);
  }
  if (!isFormData) {
    baseHeaders.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(url, {
      headers: baseHeaders,
      ...rest,
    });
  } catch {
    throw new Error(`Cannot reach API at ${API_URL}. Check backend server and CORS settings.`);
  }

  if (response.status === 401) {
    clearAuth();
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    throw new Error("Session expired");
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `API error: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}
