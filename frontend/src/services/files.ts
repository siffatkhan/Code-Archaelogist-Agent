import { api } from "./api";
import type { RepositoryFileContent, RepositoryFileNode } from "@/types/file";

/**
 * File tree + file content API calls. Matches the documented contract exactly:
 *   GET /repositories/{repository_id}/files
 *   GET /repositories/{repository_id}/files/{path}
 */
export const filesService = {
  getTree: (repositoryId: string) =>
    api.get<RepositoryFileNode[]>(`/repositories/${repositoryId}/files`),

  getFile: (repositoryId: string, path: string) =>
    api.get<RepositoryFileContent>(`/repositories/${repositoryId}/files/${encodeURIComponent(path)}`),
};
