import { useCallback, useEffect, useState } from "react";
import { USE_MOCK_DATA } from "@/lib/config";
import { filesService } from "@/services/files";
import { ApiError } from "@/types/api";
import type { RepositoryFileNode } from "@/types/file";
import { MOCK_FILE_TREE } from "./mocks/mockFiles";

export function useFileTree(repositoryId: string | undefined) {
  const [tree, setTree] = useState<RepositoryFileNode[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!repositoryId) return;
    setIsLoading(true);
    setError(null);
    try {
      if (USE_MOCK_DATA) {
        await new Promise((resolve) => setTimeout(resolve, 350));
        setTree(MOCK_FILE_TREE);
      } else {
        const data = await filesService.getTree(repositoryId);
        setTree(data);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load the file tree.");
    } finally {
      setIsLoading(false);
    }
  }, [repositoryId]);

  useEffect(() => {
    load();
  }, [load]);

  return { tree, isLoading, error, refetch: load };
}
