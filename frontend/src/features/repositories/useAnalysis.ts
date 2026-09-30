import { useCallback, useEffect, useRef, useState } from "react";
import { USE_MOCK_DATA } from "@/lib/config";
import { analysisService } from "@/services/analysis";
import { ApiError } from "@/types/api";
import type { AnalysisJobStatus } from "@/types/analysis";

const POLL_INTERVAL_MS = 2500;

interface UseAnalysisResult {
  status: AnalysisJobStatus | null;
  errorMessage: string | null;
  isStarting: boolean;
  start: () => Promise<void>;
}

/**
 * Drives the "Analyze repository" action and polls GET /analysis/{id} until the
 * job reaches a terminal state. Never fabricates progress percentages — only
 * the four backend-defined statuses are surfaced.
 */
export function useAnalysis(repositoryId: string, initialStatus: AnalysisJobStatus | null = null): UseAnalysisResult {
  const [status, setStatus] = useState<AnalysisJobStatus | null>(initialStatus);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const jobIdRef = useRef<string | null>(null);
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearPoll = useCallback(() => {
    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
  }, []);

  const pollMock = useCallback(() => {
    setStatus("running");
    pollTimeoutRef.current = setTimeout(() => {
      setStatus("completed");
    }, 3500);
  }, []);

  const poll = useCallback(
    async (jobId: string) => {
      try {
        const job = await analysisService.get(jobId);
        setStatus(job.status);
        if (job.status === "failed") {
          setErrorMessage(job.error_message ?? "Analysis failed.");
        }
        if (job.status === "queued" || job.status === "running") {
          pollTimeoutRef.current = setTimeout(() => poll(jobId), POLL_INTERVAL_MS);
        }
      } catch (err) {
        setErrorMessage(err instanceof ApiError ? err.message : "Could not check analysis status.");
      }
    },
    []
  );

  const start = useCallback(async () => {
    setIsStarting(true);
    setErrorMessage(null);
    try {
      if (USE_MOCK_DATA) {
        setStatus("queued");
        pollMock();
      } else {
        const response = await analysisService.start(repositoryId);
        jobIdRef.current = response.analysis_job_id;
        setStatus(response.status);
        poll(response.analysis_job_id);
      }
    } catch (err) {
      setErrorMessage(err instanceof ApiError ? err.message : "Could not start analysis.");
    } finally {
      setIsStarting(false);
    }
  }, [repositoryId, poll, pollMock]);

  useEffect(() => clearPoll, [clearPoll]);

  return { status, errorMessage, isStarting, start };
}
