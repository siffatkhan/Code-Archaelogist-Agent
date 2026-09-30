export type { RepositoryFileNode, RepositoryFileContent, FileNodeType } from "@/types/file";

/** Maps a file extension to a Monaco language id. */
export function detectLanguage(path: string): string {
  const ext = path.split(".").pop()?.toLowerCase();
  const map: Record<string, string> = {
    ts: "typescript",
    tsx: "typescript",
    js: "javascript",
    jsx: "javascript",
    py: "python",
    json: "json",
    md: "markdown",
    css: "css",
    html: "html",
    yml: "yaml",
    yaml: "yaml",
    go: "go",
    rs: "rust",
    java: "java",
    rb: "ruby",
    sh: "shell",
    sql: "sql",
    toml: "ini",
  };
  return map[ext ?? ""] ?? "plaintext";
}
