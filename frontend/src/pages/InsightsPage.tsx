import { useEffect, useState, type FormEvent } from "react";
import { Lightbulb, MessageCircleQuestion, ShieldAlert } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LoadingState } from "@/components/common/LoadingState";
import { ErrorState } from "@/components/common/ErrorState";
import { RepositoryBreadcrumb, WorkspaceTabs } from "@/features/repositories/RepositoryHeader";
import { useRepository } from "@/features/repositories/useRepository";
import { usePageHeader } from "@/components/layout/PageHeaderContext";
import { api } from "@/services/api";

interface RiskRecord {
  file_path: string;
  score: number;
  explanation: string;
}

interface GapRecord {
  gap_id: string;
  question: string;
  status: "open" | "resolved";
  priority: string;
}

interface QuestionResult {
  answer: string;
  confidence: string;
  classification: string;
  evidence: { path?: string; reason: string }[];
  gap_detected: boolean;
}

interface GuidanceResult {
  task: string;
  steps: { order: number; title: string; files: string[]; reasoning: string }[];
}

export default function InsightsPage() {
  const { repositoryId } = useParams<{ repositoryId: string }>();
  const navigate = useNavigate();
  const { repository, isLoading: repoLoading, error: repoError, refetch } = useRepository(repositoryId);
  const [risks, setRisks] = useState<RiskRecord[]>([]);
  const [gaps, setGaps] = useState<GapRecord[]>([]);
  const [question, setQuestion] = useState("");
  const [task, setTask] = useState("");
  const [answer, setAnswer] = useState<QuestionResult | null>(null);
  const [guidance, setGuidance] = useState<GuidanceResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  usePageHeader(
    {
      breadcrumb: repository ? <RepositoryBreadcrumb repository={repository} /> : undefined,
      actions: repository ? (
        <WorkspaceTabs
          active="insights"
          onChange={(tab) => navigate(`/repositories/${repository.repository_id}/${tab === "code" ? "explorer" : tab}`)}
        />
      ) : undefined,
    },
    [repository?.repository_id, navigate]
  );

  useEffect(() => {
    if (!repositoryId) return;
    Promise.all([
      api.get<RiskRecord[]>(`/repositories/${repositoryId}/risks`),
      api.get<GapRecord[]>(`/repositories/${repositoryId}/knowledge-gaps`),
    ])
      .then(([riskData, gapData]) => {
        setRisks(riskData);
        setGaps(gapData);
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Could not load repository insights."))
      .finally(() => setIsLoading(false));
  }, [repositoryId]);

  async function submitQuestion(event: FormEvent) {
    event.preventDefault();
    if (!repositoryId || !question.trim()) return;
    setError(null);
    try {
      setAnswer(await api.post<QuestionResult>(`/repositories/${repositoryId}/questions`, { question }));
      setQuestion("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not ask the Historian.");
    }
  }

  async function submitGuidance(event: FormEvent) {
    event.preventDefault();
    if (!repositoryId || !task.trim()) return;
    setError(null);
    try {
      setGuidance(await api.post<GuidanceResult>(`/repositories/${repositoryId}/guidance`, { task }));
      setTask("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not generate guidance.");
    }
  }

  if (repoLoading || isLoading) return <LoadingState message="Loading repository insights..." />;
  if (repoError || !repository) return <ErrorState message={repoError ?? "Repository was not found."} onRetry={refetch} />;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6 lg:p-8">
      {error && <ErrorState message={error} onRetry={() => window.location.reload()} />}
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">Repository intelligence</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-text-primary">What the code is trying to tell you</h2>
        <p className="mt-2 max-w-2xl text-sm text-text-muted">Ask why, inspect deterministic fragility signals, and capture the questions the repository cannot answer yet.</p>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.35fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><MessageCircleQuestion className="size-4 text-accent" /> Ask the Historian</CardTitle>
            <CardDescription>Answers are grounded in the analyzed repository files.</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="flex gap-2" onSubmit={submitQuestion}>
              <Input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Why does this authentication middleware exist?" />
              <Button type="submit" disabled={!question.trim()}>Ask</Button>
            </form>
            {answer && (
              <div className="mt-5 border-t border-border pt-5">
                <div className="flex items-center justify-between gap-4">
                  <p className="text-sm font-semibold text-text-primary">{answer.classification} · {answer.confidence} confidence</p>
                  {answer.gap_detected && <span className="text-xs text-warning">Knowledge gap created</span>}
                </div>
                <p className="mt-2 text-sm leading-6 text-text-secondary">{answer.answer}</p>
                {answer.evidence.length > 0 && <p className="mt-3 text-xs text-text-muted">Evidence: {answer.evidence.map((item) => item.path).filter(Boolean).join(", ")}</p>}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Lightbulb className="size-4 text-accent" /> Developer guidance</CardTitle>
            <CardDescription>Get a grounded path through the repository for a task.</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="flex gap-2" onSubmit={submitGuidance}>
              <Input value={task} onChange={(event) => setTask(event.target.value)} placeholder="Add a new authentication endpoint" />
              <Button type="submit" disabled={!task.trim()}>Plan</Button>
            </form>
            {guidance && <ol className="mt-5 space-y-4 border-t border-border pt-5">
              {guidance.steps.map((step) => <li key={step.order} className="text-sm"><p className="font-medium text-text-primary">{step.order}. {step.title}</p><p className="mt-1 text-text-secondary">{step.reasoning}</p><p className="mt-1 text-xs text-accent">{step.files.join(", ")}</p></li>)}
            </ol>}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><ShieldAlert className="size-4 text-warning" /> Fragility signals</CardTitle><CardDescription>Deterministic risk scores from repository history and structure.</CardDescription></CardHeader>
          <CardContent>
            {risks.length === 0 ? <p className="text-sm text-text-muted">Run analysis to calculate file risk.</p> : <div className="space-y-3">{risks.slice(0, 8).map((risk) => <div key={risk.file_path} className="flex items-start justify-between gap-4 border-b border-border pb-3 last:border-0 last:pb-0"><div><p className="text-sm font-medium text-text-primary">{risk.file_path}</p><p className="mt-1 text-xs text-text-muted">{risk.explanation}</p></div><span className="shrink-0 text-sm font-semibold text-warning">{Math.round(risk.score * 100)}%</span></div>)}</div>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Knowledge gaps</CardTitle><CardDescription>Questions that need a human maintainer’s answer.</CardDescription></CardHeader>
          <CardContent>
            {gaps.filter((gap) => gap.status === "open").length === 0 ? <p className="text-sm text-text-muted">No open knowledge gaps.</p> : <div className="space-y-3">{gaps.filter((gap) => gap.status === "open").map((gap) => <div key={gap.gap_id} className="border-b border-border pb-3 last:border-0 last:pb-0"><p className="text-sm text-text-primary">{gap.question}</p><p className="mt-1 text-xs uppercase tracking-wide text-warning">{gap.priority} priority</p></div>)}</div>}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}