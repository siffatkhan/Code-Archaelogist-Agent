import type { Repository } from "@/types/repository";

/**
 * Mock data for UI development only. Never imported by services/*.ts —
 * only by pages/components while the backend is not yet connected.
 * Swap USE_MOCKS off in repositories.ts / analysis.ts / files.ts once
 * the FastAPI backend is available.
 */
export const MOCK_REPOSITORIES: Repository[] = [
  {
    repository_id: "8f14e3f1-4b1a-4c1a-9c2a-111111111111",
    github_url: "https://github.com/vercel/next.js",
    owner: "vercel",
    name: "next.js",
    default_branch: "canary",
    status: "completed",
    last_analyzed_at: "2026-09-10T14:32:00Z",
    created_at: "2026-09-01T09:00:00Z",
  },
  {
    repository_id: "8f14e3f1-4b1a-4c1a-9c2a-222222222222",
    github_url: "https://github.com/fastapi/fastapi",
    owner: "fastapi",
    name: "fastapi",
    default_branch: "master",
    status: "running",
    last_analyzed_at: null,
    created_at: "2026-09-12T11:20:00Z",
  },
  {
    repository_id: "8f14e3f1-4b1a-4c1a-9c2a-333333333333",
    github_url: "https://github.com/expressjs/express",
    owner: "expressjs",
    name: "express",
    default_branch: "master",
    status: "failed",
    last_analyzed_at: "2026-09-08T08:15:00Z",
    created_at: "2026-08-29T16:44:00Z",
  },
  {
    repository_id: "8f14e3f1-4b1a-4c1a-9c2a-444444444444",
    github_url: "https://github.com/pallets/flask",
    owner: "pallets",
    name: "flask",
    default_branch: "main",
    status: "not_analyzed",
    last_analyzed_at: null,
    created_at: "2026-09-13T07:02:00Z",
  },
];
