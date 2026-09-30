import { useCallback, useEffect, useState } from "react";
import { USE_MOCK_DATA } from "@/lib/config";
import { repositoriesService } from "@/services/repositories";
import { ApiError } from "@/types/api";
import type { Repository } from "@/types/repository";
import { MOCK_REPOSITORIES } from "./mocks/mockRepositories";

interface UseRepositoryResult {
  repository: Repository | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useRepository(repositoryId: string | undefined): UseRepositoryResult {
  const [repository, setRepository] = useState<Repository | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!repositoryId) {
      setError("Repository ID is missing.");
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      if (USE_MOCK_DATA) {
        await new Promise((resolve) => setTimeout(resolve, 300));
        const found = MOCK_REPOSITORIES.find((r) => r.repository_id === repositoryId) ?? MOCK_REPOSITORIES[0];
        setRepository(found);
      } else {
        const data = await repositoriesService.get(repositoryId);
        setRepository(data);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load this repository.");
    } finally {
      setIsLoading(false);
    }
  }, [repositoryId]);

  useEffect(() => {
    load();
  }, [load]);

  return { repository, isLoading, error, refetch: load };
}
