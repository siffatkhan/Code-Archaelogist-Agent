import { api } from "./api";
import type { CreateRepositoryRequest, CreateRepositoryResponse, Repository } from "@/types/repository";

/**
 * Repository API calls. Matches the documented contract exactly:
 *   POST /repositories
 *   GET /repositories
 *   GET /repositories/{repository_id}
 *
 * No mock data lives here — see features/repositories/mocks for UI-development fixtures.
 */
export const repositoriesService = {
  create: (payload: CreateRepositoryRequest) => api.post<CreateRepositoryResponse>("/repositories", payload),

  list: () => api.get<Repository[]>("/repositories"),

  get: (repositoryId: string) => api.get<Repository>(`/repositories/${repositoryId}`),
};
