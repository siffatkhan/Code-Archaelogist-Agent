/**
 * Repository domain types.
 *
 * Field names mirror the backend API contract exactly:
 * POST /repositories -> { repository_id, github_url, status }
 * GET /repositories/{id} -> repository metadata + analysis status
 */

export type AnalysisStatus = "not_analyzed" | "queued" | "running" | "completed" | "failed";

export interface Repository {
  repository_id: string;
  github_url: string;
  /** Derived client-side for display; parsed from github_url when not provided by backend. */
  owner?: string;
  name?: string;
  default_branch?: string;
  status: AnalysisStatus | "created";
  last_analyzed_at?: string | null;
  created_at?: string;
}

export interface CreateRepositoryRequest {
  github_url: string;
}

export interface CreateRepositoryResponse {
  repository_id: string;
  github_url: string;
  status: string;
}
