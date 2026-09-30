/**
 * Repository file tree + file content types.
 *
 * GET /repositories/{repository_id}/files -> repository file tree
 * GET /repositories/{repository_id}/files/{path} -> source + metadata
 */

export type FileNodeType = "file" | "directory";

export interface RepositoryFileNode {
  path: string;
  name: string;
  type: FileNodeType;
  children?: RepositoryFileNode[];
}

export interface RepositoryFileContent {
  path: string;
  content: string;
  /** Language hint for Monaco, e.g. "typescript". Derived client-side if absent. */
  language?: string;
  size_bytes?: number;
  truncated?: boolean;
}
