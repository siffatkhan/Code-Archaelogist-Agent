import { useNavigate, useParams } from "react-router-dom";
import { PlayCircle, FolderOpen, GitBranch } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { usePageHeader } from "@/components/layout/PageHeaderContext";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { RepositoryBreadcrumb, RepositoryStatusRow, WorkspaceTabs } from "@/features/repositories/RepositoryHeader";
import { AnalysisProgress } from "@/features/repositories/AnalysisProgress";
import { useRepository } from "@/features/repositories/useRepository";
import { useAnalysis } from "@/features/repositories/useAnalysis";
import { parseOwnerAndName } from "@/features/repositories/repository.types";

export default function RepositoryPage() {
  const { repositoryId } = useParams<{ repositoryId: string }>();
  const navigate = useNavigate();
  const { repository, isLoading, error, refetch } = useRepository(repositoryId);

  const initialJobStatus =
    repository?.status === "completed" || repository?.status === "failed" || repository?.status === "running"
      ? repository.status
      : null;
  const { status: liveStatus, errorMessage, isStarting, start } = useAnalysis(repositoryId ?? "", initialJobStatus);

  usePageHeader(
    {
      breadcrumb: repository ? <RepositoryBreadcrumb repository={repository} /> : undefined,
      actions: repository ? (
        <WorkspaceTabs
          active="code"
          onChange={(tab) => navigate(`/repositories/${repository.repository_id}/${tab === "code" ? "explorer" : tab}`)}
        />
      ) : undefined,
    },
    [repository?.repository_id]
  );

  if (isLoading) {
    return <LoadingState message="Loading repository..." />;
  }

  if (error || !repository) {
    return <ErrorState message={error ?? "Repository was not found."} onRetry={refetch} />;
  }

  const { owner, name } = repository.owner
    ? { owner: repository.owner, name: repository.name ?? "" }
    : parseOwnerAndName(repository.github_url);

  const effectiveStatus = liveStatus ?? (repository.status === "created" ? "not_analyzed" : repository.status);
  const hasRunAnalysis = effectiveStatus !== "not_analyzed";

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6 lg:p-8">
      <Card className="flex flex-col gap-5 p-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-text-primary">
              {name || repository.github_url}
            </h2>
            <p className="mt-1 text-sm text-text-muted">{owner}</p>
            <a
              href={repository.github_url}
              target="_blank"
              rel="noreferrer"
              className="focus-ring mt-2 inline-block text-xs text-text-secondary hover:text-accent"
            >
              {repository.github_url}
            </a>
          </div>
          <RepositoryStatusRow repository={{ ...repository, status: effectiveStatus }} />
        </div>

        <div className="flex flex-wrap items-center gap-4 border-t border-border pt-4 text-xs text-text-muted">
          {repository.default_branch && (
            <span className="flex items-center gap-1.5">
              <GitBranch className="size-3.5" aria-hidden="true" />
              Default branch: {repository.default_branch}
            </span>
          )}
        </div>

        <div className="flex flex-wrap gap-2 border-t border-border pt-4">
          <Button onClick={start} isLoading={isStarting} disabled={effectiveStatus === "running"}>
            <PlayCircle className="size-4" aria-hidden="true" />
            Analyze repository
          </Button>
          <Button
            variant="secondary"
            onClick={() => navigate(`/repositories/${repository.repository_id}/explorer`)}
          >
            <FolderOpen className="size-4" aria-hidden="true" />
            Open explorer
          </Button>
        </div>
      </Card>

      {hasRunAnalysis ? (
        <AnalysisProgress
          status={effectiveStatus}
          errorMessage={errorMessage}
          onRetry={start}
          isRetrying={isStarting}
        />
      ) : (
        <EmptyState
          title="No analysis has been run yet."
          description="Run an analysis to build the code intelligence Code Archaeologist uses to answer why your code exists."
        />
      )}
    </div>
  );
}
