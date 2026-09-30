import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePageHeader } from "@/components/layout/PageHeaderContext";
import { RepositoryList } from "@/features/repositories/RepositoryList";
import { AddRepositoryDialog } from "@/features/repositories/AddRepositoryDialog";
import { useRepositories } from "@/features/repositories/useRepositories";

export default function RepositoriesPage() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const { repositories, isLoading, error, refetch, addRepository } = useRepositories();

  usePageHeader(
    {
      title: "Repositories",
      actions: (
        <Button size="sm" onClick={() => setDialogOpen(true)}>
          <Plus className="size-4" aria-hidden="true" />
          Add repository
        </Button>
      ),
    },
    []
  );

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6 lg:p-8">
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-text-primary">Repositories</h2>
        <p className="mt-1 text-sm text-text-muted">Your analyzed and connected codebases.</p>
      </div>

      <RepositoryList
        repositories={repositories}
        isLoading={isLoading}
        error={error}
        onRetry={refetch}
        onAddRepository={() => setDialogOpen(true)}
      />

      <AddRepositoryDialog open={dialogOpen} onOpenChange={setDialogOpen} onSubmit={addRepository} />
    </div>
  );
}
