import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import { StatusBadge } from "@/components/common/StatusBadge";
import { cn } from "@/lib/utils";
import type { AnalysisStatus, Repository } from "@/types/repository";
import { parseOwnerAndName } from "./repository.types";

export function RepositoryBreadcrumb({ repository }: { repository: Repository }) {
  const { owner, name } = repository.owner
    ? { owner: repository.owner, name: repository.name ?? "" }
    : parseOwnerAndName(repository.github_url);

  return (
    <div className="flex min-w-0 items-center gap-1.5 text-sm">
      <Link to="/repositories" className="focus-ring shrink-0 rounded text-text-muted hover:text-text-secondary">
        Code Archaeologist
      </Link>
      <ChevronRight className="size-3.5 shrink-0 text-text-muted" aria-hidden="true" />
      <span className="truncate font-medium text-text-primary">
        {owner}/{name}
      </span>
    </div>
  );
}

export type WorkspaceTab = "code" | "history" | "architecture" | "insights";

const TABS: { id: WorkspaceTab; label: string; ownedByM4: boolean }[] = [
  { id: "code", label: "Code", ownedByM4: true },
  { id: "history", label: "History", ownedByM4: true },
  { id: "architecture", label: "Architecture", ownedByM4: true },
  { id: "insights", label: "Insights", ownedByM4: true },
];

/**
 * Workspace tab strip. History and Architecture remain reserved integration
 * points, while Code and Insights are available in the current workspace.
 */
export function WorkspaceTabs({
  active,
  onChange,
}: {
  active: WorkspaceTab;
  onChange: (tab: WorkspaceTab) => void;
}) {
  return (
    <nav className="flex items-center gap-1" aria-label="Repository workspace sections">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          disabled={!tab.ownedByM4}
          onClick={() => tab.ownedByM4 && onChange(tab.id)}
          title={tab.ownedByM4 ? undefined : "Coming soon"}
          className={cn(
            "focus-ring rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
            active === tab.id && tab.ownedByM4
              ? "bg-surface-elevated text-text-primary"
              : "text-text-muted",
            tab.ownedByM4 ? "hover:bg-surface-elevated hover:text-text-primary" : "cursor-not-allowed opacity-50"
          )}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}

export function RepositoryStatusRow({ repository }: { repository: Repository }) {
  const status = (repository.status === "created" ? "not_analyzed" : repository.status) as AnalysisStatus;
  return <StatusBadge status={status} />;
}
