import { api } from "./api";
import type { AnalysisJob, StartAnalysisResponse } from "@/types/analysis";

/**
 * Analysis API calls. Matches the documented contract exactly:
 *   POST /repositories/{repository_id}/analyze
 *   GET /analysis/{analysis_job_id}
 */
export const analysisService = {
  start: (repositoryId: string) =>
    api.post<StartAnalysisResponse>(`/repositories/${repositoryId}/analyze`),

  get: (analysisJobId: string) => api.get<AnalysisJob>(`/analysis/${analysisJobId}`),
};
