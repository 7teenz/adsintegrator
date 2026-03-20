import { clearAuth } from "@/lib/auth";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api/proxy";

interface RequestOptions extends RequestInit {
  noAuth?: boolean;
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { noAuth, headers, ...rest } = options;
  const url = `${API_URL}${path}`;
  const isFormData = typeof FormData !== "undefined" && rest.body instanceof FormData;
  const baseHeaders = new Headers(headers ?? undefined);
  if (!isFormData) {
    baseHeaders.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(url, {
      credentials: "include",
      headers: baseHeaders,
      ...rest,
    });
  } catch {
    throw new Error(`Cannot reach API at ${API_URL}. Check backend server and CORS settings.`);
  }

  if (response.status === 401) {
    clearAuth();
    if (!noAuth && typeof window !== "undefined") {
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
