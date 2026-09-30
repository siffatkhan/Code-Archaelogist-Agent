export type { Repository, AnalysisStatus, CreateRepositoryRequest } from "@/types/repository";

export interface AddRepositoryFormValues {
  githubUrl: string;
}

const GITHUB_URL_PATTERN = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/?$/;

export function validateGithubUrl(url: string): string | null {
  if (!url.trim()) {
    return "GitHub repository URL is required.";
  }
  if (!GITHUB_URL_PATTERN.test(url.trim())) {
    return "Enter a valid public GitHub repository URL, e.g. https://github.com/owner/repository.";
  }
  return null;
}

/** Derives display owner/name from a github_url when the backend doesn't supply them. */
export function parseOwnerAndName(githubUrl: string): { owner: string; name: string } {
  try {
    const url = new URL(githubUrl);
    const [owner = "", name = ""] = url.pathname.replace(/^\//, "").replace(/\/$/, "").split("/");
    return { owner, name };
  } catch {
    return { owner: "", name: "" };
  }
}
