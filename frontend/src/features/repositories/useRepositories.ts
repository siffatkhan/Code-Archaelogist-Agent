import { useCallback, useEffect, useState } from "react";
import { USE_MOCK_DATA } from "@/lib/config";
import { repositoriesService } from "@/services/repositories";
import { ApiError } from "@/types/api";
import type { Repository } from "@/types/repository";
import { MOCK_REPOSITORIES } from "./mocks/mockRepositories";

interface UseRepositoriesResult {
  repositories: Repository[];
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
  addRepository: (githubUrl: string) => Promise<void>;
}

export function useRepositories(): UseRepositoriesResult {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      if (USE_MOCK_DATA) {
        await new Promise((resolve) => setTimeout(resolve, 400));
        setRepositories(MOCK_REPOSITORIES);
      } else {
        const data = await repositoriesService.list();
        setRepositories(data);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load repositories.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const addRepository = useCallback(
    async (githubUrl: string) => {
      if (USE_MOCK_DATA) {
        const newRepo: Repository = {
          repository_id: crypto.randomUUID(),
          github_url: githubUrl,
          status: "not_analyzed",
          last_analyzed_at: null,
          created_at: new Date().toISOString(),
        };
        setRepositories((prev) => [newRepo, ...prev]);
        return;
      }

      await repositoriesService.create({ github_url: githubUrl });
      await load();
    },
    [load]
  );

  return { repositories, isLoading, error, refetch: load, addRepository };
}
