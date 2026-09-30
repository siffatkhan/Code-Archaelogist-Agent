import { useNavigate } from "react-router-dom";
import { LoginForm } from "@/features/auth/LoginForm";

export default function LoginPage() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg px-4">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            "radial-gradient(circle at 20% 20%, rgba(217,138,74,0.08), transparent 40%), radial-gradient(circle at 80% 60%, rgba(96,165,250,0.06), transparent 45%)",
        }}
        aria-hidden="true"
      />

      <div className="relative z-10 w-full max-w-sm animate-slide-up">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <div className="flex size-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
            <span className="font-mono text-base font-bold">CA</span>
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-text-primary">
              Code Archaeologist
            </h1>
            <p className="mt-1 text-sm text-text-muted">Excavate the story behind your code.</p>
          </div>
        </div>

        <div className="rounded-lg border border-border bg-surface p-6 shadow-xl shadow-black/20">
          <LoginForm onSuccess={() => navigate("/dashboard", { replace: true })} />
        </div>

        <p className="mt-6 text-center text-xs text-text-muted">
          Public repositories only. Your GitHub credentials are never requested.
        </p>
      </div>
    </div>
  );
}
