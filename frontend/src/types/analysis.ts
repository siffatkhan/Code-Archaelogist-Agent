/**
 * Analysis job types.
 *
 * POST /repositories/{repository_id}/analyze -> { analysis_job_id, status: "queued" }
 * GET /analysis/{analysis_job_id} -> { analysis_job_id, status }
 *
 * Allowed statuses: queued | running | completed | failed
 */

export type AnalysisJobStatus = "queued" | "running" | "completed" | "failed";

export interface AnalysisJob {
  analysis_job_id: string;
  status: AnalysisJobStatus;
  error_message?: string;
}

export interface StartAnalysisResponse {
  analysis_job_id: string;
  status: AnalysisJobStatus;
}
