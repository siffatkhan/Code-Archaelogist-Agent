import { useMemo, useState } from "react";
import { Search, FolderX } from "lucide-react";
import { SkeletonRows } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { FileTreeItem } from "./FileTreeItem";
import type { RepositoryFileNode } from "@/types/file";

interface FileTreeProps {
  tree: RepositoryFileNode[];
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
  selectedPath: string | null;
  onSelectFile: (path: string) => void;
}

function filterTree(nodes: RepositoryFileNode[], query: string): RepositoryFileNode[] {
  if (!query.trim()) return nodes;
  const lowerQuery = query.toLowerCase();

  return nodes.reduce<RepositoryFileNode[]>((acc, node) => {
    if (node.type === "file") {
      if (node.name.toLowerCase().includes(lowerQuery)) acc.push(node);
      return acc;
    }
    const filteredChildren = filterTree(node.children ?? [], query);
    if (filteredChildren.length > 0 || node.name.toLowerCase().includes(lowerQuery)) {
      acc.push({ ...node, children: filteredChildren });
    }
    return acc;
  }, []);
}

export function FileTree({ tree, isLoading, error, onRetry, selectedPath, onSelectFile }: FileTreeProps) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => filterTree(tree, query), [tree, query]);

  return (
    <div className="flex h-full flex-col border-r border-border bg-surface">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2.5">
        <Search className="size-3.5 shrink-0 text-text-muted" aria-hidden="true" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter files"
          className="focus-ring w-full bg-transparent text-[13px] text-text-primary placeholder:text-text-muted"
          aria-label="Filter files"
        />
      </div>

      <div className="flex-1 overflow-y-auto py-1.5">
        {isLoading ? (
          <SkeletonRows count={5} className="mx-2" />
        ) : error ? (
          <ErrorState message={error} onRetry={onRetry} className="border-none bg-transparent py-8" />
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={FolderX}
            title="No files available."
            description={query ? "No files match your filter." : undefined}
            className="border-none py-8"
          />
        ) : (
          filtered.map((node) => (
            <FileTreeItem
              key={node.path}
              node={node}
              depth={0}
              selectedPath={selectedPath}
              onSelectFile={onSelectFile}
            />
          ))
        )}
      </div>
    </div>
  );
}
