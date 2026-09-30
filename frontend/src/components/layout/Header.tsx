import type { ReactNode } from "react";
import { Search } from "lucide-react";

interface HeaderProps {
  title?: string;
  breadcrumb?: ReactNode;
  actions?: ReactNode;
}

export function Header({ title, breadcrumb, actions }: HeaderProps) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-border bg-surface/60 px-5 backdrop-blur-sm">
      <div className="flex min-w-0 items-center gap-2">
        {breadcrumb ? (
          breadcrumb
        ) : (
          <h1 className="truncate text-sm font-medium text-text-primary">{title}</h1>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <button
          type="button"
          className="focus-ring hidden items-center gap-2 rounded-md border border-border bg-surface-elevated px-2.5 py-1.5 text-xs text-text-muted transition-colors hover:border-border-strong hover:text-text-secondary sm:flex"
        >
          <Search className="size-3.5" aria-hidden="true" />
          <span>Search repositories</span>
          <kbd className="ml-3 rounded border border-border bg-surface px-1 font-mono text-[10px] text-text-muted">
            ⌘K
          </kbd>
        </button>
        {actions}
      </div>
    </header>
  );
}
