import { ArrowUpRight, GitBranch } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/common/StatusBadge";
import type { AnalysisStatus, Repository } from "@/types/repository";
import { parseOwnerAndName } from "./repository.types";

function toAnalysisStatus(status: Repository["status"]): AnalysisStatus {
  return status === "created" ? "not_analyzed" : status;
}

function formatTimestamp(value?: string | null): string {
  if (!value) return "Never";
  try {
    return new Date(value).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}

export function RepositoryCard({ repository }: { repository: Repository }) {
  const navigate = useNavigate();
  const { owner, name } = repository.owner
    ? { owner: repository.owner, name: repository.name ?? "" }
    : parseOwnerAndName(repository.github_url);

  const status = toAnalysisStatus(repository.status);

  return (
    <Card className="group flex flex-col gap-4 p-5 transition-colors hover:border-border-strong">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-text-primary">{name || repository.github_url}</p>
          <p className="truncate text-xs text-text-muted">{owner}</p>
        </div>
        <StatusBadge status={status} />
      </div>

      <a
        href={repository.github_url}
        target="_blank"
        rel="noreferrer"
        className="focus-ring group/link flex items-center gap-1.5 truncate text-xs text-text-secondary hover:text-accent"
      >
        <span className="truncate">{repository.github_url.replace("https://", "")}</span>
        <ArrowUpRight className="size-3 shrink-0 opacity-0 transition-opacity group-hover/link:opacity-100" />
      </a>

      <div className="flex items-center justify-between border-t border-border pt-3">
        <div className="flex items-center gap-3 text-xs text-text-muted">
          {repository.default_branch && (
            <span className="flex items-center gap-1">
              <GitBranch className="size-3" aria-hidden="true" />
              {repository.default_branch}
            </span>
          )}
          <span>Analyzed {formatTimestamp(repository.last_analyzed_at)}</span>
        </div>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => navigate(`/repositories/${repository.repository_id}`)}
        >
          Open
        </Button>
      </div>
    </Card>
  );
}
