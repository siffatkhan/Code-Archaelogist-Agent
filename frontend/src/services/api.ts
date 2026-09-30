import { supabase } from "@/lib/supabase";
import { ApiError, type ApiErrorResponse } from "@/types/api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string | undefined;

if (!API_BASE_URL) {
  // eslint-disable-next-line no-console
  console.warn("[api] VITE_API_BASE_URL is not set. API requests will fail until it is configured.");
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
};

async function getAuthHeader(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Parses the backend error contract:
 * { "error": { "code": "REPOSITORY_NOT_FOUND", "message": "Repository was not found." } }
 * Falls back to a safe generic message if the body doesn't match the contract.
 */
async function parseErrorResponse(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as ApiErrorResponse;
    if (body?.error?.message) {
      return new ApiError(body.error.message, body.error.code ?? "UNKNOWN_ERROR", response.status);
    }
  } catch {
    // Body wasn't JSON or didn't match the contract — fall through to generic message.
  }

  return new ApiError(
    "Something went wrong while talking to the server. Please try again.",
    "UNKNOWN_ERROR",
    response.status
  );
}

/**
 * Core request function. All service modules (repositories.ts, analysis.ts, files.ts)
 * should route through this rather than calling fetch directly.
 */
export async function apiRequest<TResponse>(path: string, options: RequestOptions = {}): Promise<TResponse> {
  if (!API_BASE_URL) {
    throw new ApiError(
      "API base URL is not configured. Set VITE_API_BASE_URL in your environment.",
      "CONFIGURATION_ERROR"
    );
  }

  const authHeader = await getAuthHeader();
  const { body, headers, ...rest } = options;

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      headers: {
        "Content-Type": "application/json",
        ...authHeader,
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Could not reach the server. Check your connection and try again.", "NETWORK_ERROR");
  }

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  if (response.status === 204) {
    return undefined as TResponse;
  }

  return (await response.json()) as TResponse;
}

export const api = {
  get: <T>(path: string) => apiRequest<T>(path, { method: "GET" }),
  post: <T>(path: string, body?: unknown) => apiRequest<T>(path, { method: "POST", body }),
};
