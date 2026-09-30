/**
 * Shared API-level types matching the backend error contract exactly.
 *
 * Backend errors always take the shape:
 * { "error": { "code": "REPOSITORY_NOT_FOUND", "message": "Repository was not found." } }
 */

export interface ApiErrorBody {
  code: string;
  message: string;
}

export interface ApiErrorResponse {
  error: ApiErrorBody;
}

/**
 * Normalized error thrown by the API client for consumption by UI layers.
 * Always carries a user-safe message — never a raw stack trace.
 */
export class ApiError extends Error {
  code: string;
  status?: number;

  constructor(message: string, code = "UNKNOWN_ERROR", status?: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

/** Generic wrapper for GET /repositories style list responses, if the backend paginates. */
export interface ListResponse<T> {
  items: T[];
}
