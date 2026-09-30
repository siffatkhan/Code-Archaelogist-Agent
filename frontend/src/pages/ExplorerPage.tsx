import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { usePageHeader } from "@/components/layout/PageHeaderContext";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { RepositoryBreadcrumb, WorkspaceTabs } from "@/features/repositories/RepositoryHeader";
import { useRepository } from "@/features/repositories/useRepository";
import { FileTree } from "@/features/explorer/FileTree";
import { CodeViewer } from "@/features/explorer/CodeViewer";
import { useFileTree } from "@/features/explorer/useFileTree";
import { useFileContent } from "@/features/explorer/useFileContent";

export default function ExplorerPage() {
  const { repositoryId } = useParams<{ repositoryId: string }>();
  const navigate = useNavigate();
  const { repository, isLoading: repoLoading, error: repoError, refetch: refetchRepo } = useRepository(repositoryId);
  const { tree, isLoading: treeLoading, error: treeError, refetch: refetchTree } = useFileTree(repositoryId);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const { file, isLoading: fileLoading, error: fileError, refetch: refetchFile } = useFileContent(
    repositoryId,
    selectedPath
  );

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

  if (repoLoading) {
    return <LoadingState message="Loading repository..." />;
  }

  if (repoError || !repository) {
    return <ErrorState message={repoError ?? "Repository was not found."} onRetry={refetchRepo} />;
  }

  return (
    <div className="flex min-h-0 flex-1">
      <div className="w-64 shrink-0 lg:w-72">
        <FileTree
          tree={tree}
          isLoading={treeLoading}
          error={treeError}
          onRetry={refetchTree}
          selectedPath={selectedPath}
          onSelectFile={setSelectedPath}
        />
      </div>
      <div className="min-w-0 flex-1 overflow-x-auto">
        <CodeViewer file={file} isLoading={fileLoading} error={fileError} onRetry={refetchFile} />
      </div>
    </div>
  );
}
