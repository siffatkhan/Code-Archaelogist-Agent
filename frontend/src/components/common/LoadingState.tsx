import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface LoadingStateProps {
  message?: string;
  className?: string;
  /** Compact inline spinner instead of a full centered block. */
  inline?: boolean;
}

export function LoadingState({ message = "Loading...", className, inline = false }: LoadingStateProps) {
  if (inline) {
    return (
      <div className={cn("flex items-center gap-2 text-sm text-text-muted", className)} role="status">
        <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
        <span>{message}</span>
      </div>
    );
  }

  return (
    <div
      className={cn("flex flex-1 flex-col items-center justify-center gap-3 py-16 text-center", className)}
      role="status"
      aria-live="polite"
    >
      <Loader2 className="size-5 animate-spin text-text-muted" aria-hidden="true" />
      <p className="text-sm text-text-muted">{message}</p>
    </div>
  );
}

interface SkeletonRowsProps {
  count?: number;
  className?: string;
}

/** Skeleton placeholder rows for list-style loading (e.g. repository cards). */
export function SkeletonRows({ count = 3, className }: SkeletonRowsProps) {
  return (
    <div className={cn("flex flex-col gap-3", className)} aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="skeleton h-24 rounded-lg border border-border" />
      ))}
    </div>
  );
}
