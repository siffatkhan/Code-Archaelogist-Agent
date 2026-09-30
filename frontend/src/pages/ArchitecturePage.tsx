import { Boxes, FileCode2, FolderTree } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { usePageHeader } from "@/components/layout/PageHeaderContext";
import { RepositoryBreadcrumb, WorkspaceTabs } from "@/features/repositories/RepositoryHeader";
import { useRepository } from "@/features/repositories/useRepository";
import { api } from "@/services/api";

interface ArchitectureNode { id: string; label: string; path: string; type: "directory" | "file"; entity_count: number; }
interface ArchitectureEdge { source: string; target: string; type: string; }

export default function ArchitecturePage() {
  const { repositoryId } = useParams<{ repositoryId: string }>();
  const navigate = useNavigate();
  const { repository, isLoading: repoLoading, error: repoError, refetch } = useRepository(repositoryId);
  const [nodes, setNodes] = useState<ArchitectureNode[]>([]);
  const [edges, setEdges] = useState<ArchitectureEdge[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  usePageHeader({
    breadcrumb: repository ? <RepositoryBreadcrumb repository={repository} /> : undefined,
    actions: repository ? <WorkspaceTabs active="architecture" onChange={(tab) => navigate(`/repositories/${repository.repository_id}/${tab === "code" ? "explorer" : tab}`)} /> : undefined,
  }, [repository?.repository_id, navigate]);

  useEffect(() => {
    if (!repositoryId) return;
    api.get<{ nodes: ArchitectureNode[]; edges: ArchitectureEdge[] }>(`/repositories/${repositoryId}/architecture`)
      .then((result) => { setNodes(result.nodes); setEdges(result.edges); })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Could not load architecture."))
      .finally(() => setIsLoading(false));
  }, [repositoryId]);

  if (repoLoading || isLoading) return <LoadingState message="Mapping repository architecture..." />;
  if (repoError || !repository) return <ErrorState message={repoError ?? "Repository was not found."} onRetry={refetch} />;
  if (error) return <ErrorState message={error} onRetry={() => window.location.reload()} />;

  const directories = nodes.filter((node) => node.type === "directory");
  const files = nodes.filter((node) => node.type === "file");
  return <div className="mx-auto w-full max-w-6xl p-6 lg:p-8">
    <div className="mb-6"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">Repository architecture</p><h2 className="mt-2 text-2xl font-semibold text-text-primary">How the repository is shaped</h2><p className="mt-2 text-sm text-text-muted">A structural map of analyzed directories, files, and extracted code entities.</p></div>
    <div className="mb-5 grid gap-4 sm:grid-cols-3"><Card><CardContent className="flex items-center gap-3 pt-5"><FolderTree className="size-5 text-accent" /><div><p className="text-2xl font-semibold text-text-primary">{directories.length}</p><p className="text-xs text-text-muted">Directories</p></div></CardContent></Card><Card><CardContent className="flex items-center gap-3 pt-5"><FileCode2 className="size-5 text-info" /><div><p className="text-2xl font-semibold text-text-primary">{files.length}</p><p className="text-xs text-text-muted">Files</p></div></CardContent></Card><Card><CardContent className="flex items-center gap-3 pt-5"><Boxes className="size-5 text-warning" /><div><p className="text-2xl font-semibold text-text-primary">{files.reduce((total, file) => total + file.entity_count, 0)}</p><p className="text-xs text-text-muted">Code entities</p></div></CardContent></Card></div>
    <Card><CardHeader><CardTitle>Module map</CardTitle></CardHeader><CardContent><div className="grid gap-3 md:grid-cols-2">{nodes.map((node) => <div key={node.id} className="flex items-center justify-between border-b border-border py-3 last:border-0"><div className="flex min-w-0 items-center gap-3">{node.type === "directory" ? <FolderTree className="size-4 shrink-0 text-accent" /> : <FileCode2 className="size-4 shrink-0 text-info" />}<span className="truncate font-mono text-sm text-text-primary">{node.path}</span></div>{node.type === "file" && <span className="shrink-0 text-xs text-text-muted">{node.entity_count} entities</span>}</div>)}</div>{edges.length > 0 && <p className="mt-5 text-xs text-text-muted">{edges.length} containment relationships mapped from the repository tree.</p>}</CardContent></Card>
  </div>;
}