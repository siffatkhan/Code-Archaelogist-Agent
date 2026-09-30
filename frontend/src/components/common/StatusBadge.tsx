import { CheckCircle2, CircleDashed, Loader2, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { AnalysisStatus } from "@/types/repository";

const STATUS_CONFIG: Record<
  AnalysisStatus,
  { label: string; variant: "neutral" | "accent" | "success" | "warning" | "error"; icon: typeof CheckCircle2 }
> = {
  not_analyzed: { label: "Not analyzed", variant: "neutral", icon: CircleDashed },
  queued: { label: "Queued", variant: "warning", icon: CircleDashed },
  running: { label: "Analyzing", variant: "accent", icon: Loader2 },
  completed: { label: "Completed", variant: "success", icon: CheckCircle2 },
  failed: { label: "Failed", variant: "error", icon: XCircle },
};

interface StatusBadgeProps {
  status: AnalysisStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.not_analyzed;
  const Icon = config.icon;

  return (
    <Badge variant={config.variant}>
      <Icon className={Icon === Loader2 ? "size-3 animate-spin" : "size-3"} aria-hidden="true" />
      {config.label}
    </Badge>
  );
}
