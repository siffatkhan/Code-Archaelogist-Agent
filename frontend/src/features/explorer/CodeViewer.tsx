import Editor from "@monaco-editor/react";
import { FileCode2 } from "lucide-react";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import type { RepositoryFileContent } from "@/types/file";

interface CodeViewerProps {
  file: RepositoryFileContent | null;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function CodeViewer({ file, isLoading, error, onRetry }: CodeViewerProps) {
  return (
    <div className="flex h-full min-w-0 flex-col bg-surface">
      {file && (
        <div className="flex shrink-0 items-center gap-2 border-b border-border px-4 py-2.5">
          <FileCode2 className="size-3.5 shrink-0 text-text-muted" aria-hidden="true" />
          <span className="truncate font-mono text-[13px] text-text-secondary">{file.path}</span>
          {file.truncated && (
            <span className="ml-2 shrink-0 rounded border border-warning/30 bg-warning-muted px-1.5 py-0.5 text-[10px] text-warning">
              Truncated
            </span>
          )}
        </div>
      )}

      <div className="min-h-0 flex-1">
        {isLoading ? (
          <LoadingState message="Loading source..." />
        ) : error ? (
          <ErrorState message={error} onRetry={onRetry} className="h-full" />
        ) : !file ? (
          <EmptyState
            icon={FileCode2}
            title="Select a file to view its source."
            description="Choose a file from the tree on the left to open it here."
            className="h-full border-none"
          />
        ) : (
          <Editor
            key={file.path}
            language={file.language ?? "plaintext"}
            value={file.content}
            theme="vs-dark"
            options={{
              readOnly: true,
              domReadOnly: true,
              minimap: { enabled: true },
              fontSize: 13,
              fontFamily: "JetBrains Mono, monospace",
              lineNumbers: "on",
              scrollBeyondLastLine: false,
              smoothScrolling: true,
              renderLineHighlight: "none",
              contextmenu: false,
              automaticLayout: true,
              padding: { top: 12 },
            }}
            loading={<LoadingState message="Loading editor..." />}
          />
        )}
      </div>
    </div>
  );
}
