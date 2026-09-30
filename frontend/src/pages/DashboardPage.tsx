import { useMemo, useState } from "react";
import { FolderGit2, Activity, AlertTriangle, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { usePageHeader } from "@/components/layout/PageHeaderContext";
import { EmptyState } from "@/components/common/EmptyState";
import { SkeletonRows } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { RepositoryCard } from "@/features/repositories/RepositoryCard";
import { AddRepositoryDialog } from "@/features/repositories/AddRepositoryDialog";
import { useRepositories } from "@/features/repositories/useRepositories";

export default function DashboardPage() {
  usePageHeader({ title: "Overview" }, []);
  const { repositories, isLoading, error, refetch, addRepository } = useRepositories();
  const [dialogOpen, setDialogOpen] = useState(false);

  const stats = useMemo(() => {
    const total = repositories.length;
    const analyses = repositories.filter((r) => r.status === "completed" || r.status === "running").length;
    const needsAttention = repositories.filter((r) => r.status === "failed").length;
    return { total, analyses, needsAttention };
  }, [repositories]);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 p-6 lg:p-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-text-primary">Good morning, Developer.</h2>
          <p className="mt-1 max-w-xl text-sm text-text-muted">
            Understand the history, decisions, and risks hidden inside your codebase.
          </p>
        </div>
        <Button onClick={() => setDialogOpen(true)} size="lg">
          <Plus className="size-4" aria-hidden="true" />
          Add repository
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <SummaryCard icon={FolderGit2} label="Repositories" value={stats.total} />
        <SummaryCard icon={Activity} label="Analyses" value={stats.analyses} />
        <SummaryCard
          icon={AlertTriangle}
          label="Repositories needing attention"
          value={stats.needsAttention}
          tone={stats.needsAttention > 0 ? "warning" : "default"}
        />
      </div>

      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-text-primary">Recent repositories</h3>
        </div>

        {isLoading ? (
          <SkeletonRows count={3} />
        ) : error ? (
          <ErrorState message={error} onRetry={refetch} />
        ) : repositories.length === 0 ? (
          <EmptyState
            icon={FolderGit2}
            title="Your repository workspace is empty."
            description="Add a public GitHub repository to begin excavating its history."
            action={<Button onClick={() => setDialogOpen(true)}>Add repository</Button>}
          />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {repositories.slice(0, 6).map((repo) => (
              <RepositoryCard key={repo.repository_id} repository={repo} />
            ))}
          </div>
        )}
      </div>

      <AddRepositoryDialog open={dialogOpen} onOpenChange={setDialogOpen} onSubmit={addRepository} />
    </div>
  );
}

function SummaryCard({
  icon: Icon,
  label,
  value,
  tone = "default",
}: {
  icon: typeof FolderGit2;
  label: string;
  value: number;
  tone?: "default" | "warning";
}) {
  return (
    <Card className="flex items-center gap-4 p-5">
      <div
        className={
          tone === "warning"
            ? "flex size-10 shrink-0 items-center justify-center rounded-md border border-warning/30 bg-warning-muted text-warning"
            : "flex size-10 shrink-0 items-center justify-center rounded-md border border-border bg-surface-elevated text-text-secondary"
        }
      >
        <Icon className="size-5" aria-hidden="true" />
      </div>
      <div>
        <p className="text-2xl font-semibold tabular-nums text-text-primary">{value}</p>
        <p className="text-xs text-text-muted">{label}</p>
      </div>
    </Card>
  );
}
