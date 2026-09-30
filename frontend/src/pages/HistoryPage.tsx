import { GitCommitHorizontal } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { usePageHeader } from "@/components/layout/PageHeaderContext";
import { RepositoryBreadcrumb, WorkspaceTabs } from "@/features/repositories/RepositoryHeader";
import { useRepository } from "@/features/repositories/useRepository";
import { api } from "@/services/api";

interface Commit { hash: string; author: string; message: string; timestamp?: string; }

export default function HistoryPage() {
  const { repositoryId } = useParams<{ repositoryId: string }>();
  const navigate = useNavigate();
  const { repository, isLoading: repoLoading, error: repoError, refetch } = useRepository(repositoryId);
  const [commits, setCommits] = useState<Commit[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  usePageHeader({
    breadcrumb: repository ? <RepositoryBreadcrumb repository={repository} /> : undefined,
    actions: repository ? <WorkspaceTabs active="history" onChange={(tab) => navigate(`/repositories/${repository.repository_id}/${tab === "code" ? "explorer" : tab}`)} /> : undefined,
  }, [repository?.repository_id, navigate]);

  useEffect(() => {
    if (!repositoryId) return;
    api.get<{ commits: Commit[] }>(`/repositories/${repositoryId}/history`)
      .then((result) => setCommits(result.commits))
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Could not load history."))
      .finally(() => setIsLoading(false));
  }, [repositoryId]);

  if (repoLoading || isLoading) return <LoadingState message="Loading repository history..." />;
  if (repoError || !repository) return <ErrorState message={repoError ?? "Repository was not found."} onRetry={refetch} />;
  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />;

  return <div className="mx-auto w-full max-w-4xl p-6 lg:p-8">
    <div className="mb-6"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">Repository history</p><h2 className="mt-2 text-2xl font-semibold text-text-primary">The decisions behind the code</h2><p className="mt-2 text-sm text-text-muted">Recent commits imported from the analyzed public repository.</p></div>
    <Card><CardHeader><CardTitle>{commits.length} commits captured</CardTitle></CardHeader><CardContent>{commits.length === 0 ? <p className="text-sm text-text-muted">No commit history was available for this analysis.</p> : <div className="space-y-5">{commits.map((commit) => <article key={commit.hash} className="relative border-l border-border pl-6"><GitCommitHorizontal className="absolute -left-2.5 top-0.5 size-5 bg-surface text-accent" /><p className="text-sm font-medium text-text-primary">{commit.message.split("\n")[0]}</p><p className="mt-1 text-xs text-text-muted">{commit.author}{commit.timestamp ? ` · ${new Date(commit.timestamp).toLocaleDateString()}` : ""}</p><p className="mt-1 font-mono text-[11px] text-text-muted">{commit.hash.slice(0, 10)}</p></article>)}</div>}</CardContent></Card>
  </div>;
}