import { useState } from "react";
import { ChevronRight, Folder, FolderOpen, File, FileCode2, FileJson, FileText } from "lucide-react";
import { cn } from "@/lib/utils";
import type { RepositoryFileNode } from "@/types/file";

function FileIcon({ name }: { name: string }) {
  const ext = name.split(".").pop()?.toLowerCase();
  if (["ts", "tsx", "js", "jsx", "py", "go", "rs", "java", "rb"].includes(ext ?? "")) {
    return <FileCode2 className="size-3.5 text-info" aria-hidden="true" />;
  }
  if (ext === "json") {
    return <FileJson className="size-3.5 text-warning" aria-hidden="true" />;
  }
  if (ext === "md") {
    return <FileText className="size-3.5 text-text-muted" aria-hidden="true" />;
  }
  return <File className="size-3.5 text-text-muted" aria-hidden="true" />;
}

interface FileTreeItemProps {
  node: RepositoryFileNode;
  depth: number;
  selectedPath: string | null;
  onSelectFile: (path: string) => void;
}

export function FileTreeItem({ node, depth, selectedPath, onSelectFile }: FileTreeItemProps) {
  const [expanded, setExpanded] = useState(depth === 0);
  const isDirectory = node.type === "directory";
  const isSelected = selectedPath === node.path;

  return (
    <div>
      <button
        type="button"
        onClick={() => (isDirectory ? setExpanded((e) => !e) : onSelectFile(node.path))}
        style={{ paddingLeft: `${depth * 14 + 10}px` }}
        className={cn(
          "focus-ring flex w-full items-center gap-1.5 rounded-md py-1 pr-2 text-left text-[13px] transition-colors",
          isSelected
            ? "bg-accent-muted text-text-primary"
            : "text-text-secondary hover:bg-surface-elevated hover:text-text-primary"
        )}
        aria-expanded={isDirectory ? expanded : undefined}
        aria-current={isSelected ? "true" : undefined}
      >
        {isDirectory ? (
          <>
            <ChevronRight
              className={cn("size-3.5 shrink-0 text-text-muted transition-transform", expanded && "rotate-90")}
              aria-hidden="true"
            />
            {expanded ? (
              <FolderOpen className="size-3.5 shrink-0 text-accent-hover" aria-hidden="true" />
            ) : (
              <Folder className="size-3.5 shrink-0 text-text-muted" aria-hidden="true" />
            )}
          </>
        ) : (
          <>
            <span className="size-3.5 shrink-0" />
            <FileIcon name={node.name} />
          </>
        )}
        <span className="truncate">{node.name}</span>
      </button>

      {isDirectory && expanded && node.children && (
        <div>
          {node.children.map((child) => (
            <FileTreeItem
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              onSelectFile={onSelectFile}
            />
          ))}
        </div>
      )}
    </div>
  );
}
