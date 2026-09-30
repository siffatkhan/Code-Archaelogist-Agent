import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-bg px-4 text-center">
      <div className="flex size-12 items-center justify-center rounded-full border border-border bg-surface-elevated text-text-muted">
        <Compass className="size-5" aria-hidden="true" />
      </div>
      <div>
        <h1 className="text-lg font-semibold text-text-primary">Page not found</h1>
        <p className="mt-1 text-sm text-text-muted">
          This part of the codebase hasn't been excavated yet.
        </p>
      </div>
      <Button asChild>
        <Link to="/dashboard">Back to dashboard</Link>
      </Button>
    </div>
  );
}
