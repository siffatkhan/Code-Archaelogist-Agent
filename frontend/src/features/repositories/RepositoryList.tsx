import { FolderGit2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SkeletonRows } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { RepositoryCard } from "./RepositoryCard";
import type { Repository } from "@/types/repository";

interface RepositoryListProps {
  repositories: Repository[];
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
  onAddRepository: () => void;
}

export function RepositoryList({ repositories, isLoading, error, onRetry, onAddRepository }: RepositoryListProps) {
  if (isLoading) {
    return <SkeletonRows count={4} className="p-1" />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={onRetry} />;
  }

  if (repositories.length === 0) {
    return (
      <EmptyState
        icon={FolderGit2}
        title="No repositories yet."
        description="Connect a public GitHub repository to start exploring its codebase."
        action={<Button onClick={onAddRepository}>Add repository</Button>}
      />
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {repositories.map((repo) => (
        <RepositoryCard key={repo.repository_id} repository={repo} />
      ))}
    </div>
  );
}
