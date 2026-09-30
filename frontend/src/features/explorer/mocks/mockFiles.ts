import type { RepositoryFileContent, RepositoryFileNode } from "@/types/file";

/**
 * Mock data for UI development only. Not imported by services/files.ts.
 */
export const MOCK_FILE_TREE: RepositoryFileNode[] = [
  {
    path: "src",
    name: "src",
    type: "directory",
    children: [
      {
        path: "src/auth",
        name: "auth",
        type: "directory",
        children: [
          { path: "src/auth/login.ts", name: "login.ts", type: "file" },
          { path: "src/auth/middleware.ts", name: "middleware.ts", type: "file" },
        ],
      },
      {
        path: "src/services",
        name: "services",
        type: "directory",
        children: [{ path: "src/services/httpClient.ts", name: "httpClient.ts", type: "file" }],
      },
      {
        path: "src/utils",
        name: "utils",
        type: "directory",
        children: [{ path: "src/utils/logger.ts", name: "logger.ts", type: "file" }],
      },
      { path: "src/index.ts", name: "index.ts", type: "file" },
    ],
  },
  { path: "package.json", name: "package.json", type: "file" },
  { path: "README.md", name: "README.md", type: "file" },
];

export const MOCK_FILE_CONTENTS: Record<string, RepositoryFileContent> = {
  "src/auth/middleware.ts": {
    path: "src/auth/middleware.ts",
    language: "typescript",
    content: `import type { Request, Response, NextFunction } from "express";
import { verifyToken } from "./login";

// This middleware was introduced in commit a3f9c21 after an incident
// where unauthenticated requests reached the billing endpoints.
export function middleware(req: Request, res: Response, next: NextFunction) {
  const header = req.headers.authorization;

  if (!header) {
    return res.status(401).json({ error: "Missing authorization header" });
  }

  const token = header.replace("Bearer ", "");

  try {
    req.user = verifyToken(token);
    next();
  } catch {
    res.status(401).json({ error: "Invalid token" });
  }
}
`,
  },
};
