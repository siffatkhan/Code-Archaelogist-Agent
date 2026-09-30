import { CheckCircle2, Loader2, XCircle, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { AnalysisJobStatus } from "@/types/analysis";

interface AnalysisProgressProps {
  status: AnalysisJobStatus;
  errorMessage?: string | null;
  onRetry: () => void;
  isRetrying?: boolean;
}

const COPY: Record<AnalysisJobStatus, { title: string; description: string }> = {
  queued: {
    title: "Analysis queued",
    description: "Code Archaeologist is preparing to examine this repository.",
  },
  running: {
    title: "Analyzing repository",
    description: "Code Archaeologist is examining the repository structure and history.",
  },
  completed: {
    title: "Analysis complete",
    description: "The repository has been analyzed and is ready to explore.",
  },
  failed: {
    title: "Analysis failed",
    description: "Something went wrong while analyzing this repository.",
  },
};

export function AnalysisProgress({ status, errorMessage, onRetry, isRetrying }: AnalysisProgressProps) {
  const copy = COPY[status];

  return (
    <Card className="flex flex-col items-center gap-4 p-8 text-center">
      <div
        className={
          status === "failed"
            ? "flex size-12 items-center justify-center rounded-full border border-error/30 bg-error-muted text-error"
            : status === "completed"
              ? "flex size-12 items-center justify-center rounded-full border border-success/30 bg-success-muted text-success"
              : "flex size-12 items-center justify-center rounded-full border border-accent/30 bg-accent-muted text-accent-hover"
        }
      >
        {status === "queued" && <Clock className="size-5" aria-hidden="true" />}
        {status === "running" && <Loader2 className="size-5 animate-spin" aria-hidden="true" />}
        {status === "completed" && <CheckCircle2 className="size-5" aria-hidden="true" />}
        {status === "failed" && <XCircle className="size-5" aria-hidden="true" />}
      </div>

      <div>
        <p className="text-sm font-semibold text-text-primary">{copy.title}</p>
        <p className="mt-1 max-w-sm text-sm text-text-muted">
          {status === "failed" && errorMessage ? errorMessage : copy.description}
        </p>
      </div>

      {status === "failed" && (
        <Button variant="outline" size="sm" onClick={onRetry} isLoading={isRetrying}>
          Retry analysis
        </Button>
      )}
    </Card>
  );
}
