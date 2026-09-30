import { LogOut } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/features/auth/AuthContext";
import { cn } from "@/lib/utils";

interface UserMenuProps {
  collapsed: boolean;
}

export function UserMenu({ collapsed }: UserMenuProps) {
  const { session, signOut } = useAuth();
  const navigate = useNavigate();

  const email = session?.user.email ?? "guest@local";
  const initials = email.slice(0, 2).toUpperCase();

  async function handleLogout() {
    await signOut();
    navigate("/login", { replace: true });
  }

  return (
    <div
      className={cn(
        "flex items-center gap-2.5 rounded-md px-2.5 py-2",
        collapsed && "justify-center px-0"
      )}
    >
      <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-surface-elevated text-xs font-medium text-text-secondary">
        {initials}
      </div>
      {!collapsed && (
        <>
          <span className="min-w-0 flex-1 truncate text-xs text-text-secondary">{email}</span>
          <button
            type="button"
            onClick={handleLogout}
            className="focus-ring rounded-md p-1.5 text-text-muted transition-colors hover:bg-surface-hover hover:text-error"
            aria-label="Log out"
            title="Log out"
          >
            <LogOut className="size-3.5" aria-hidden="true" />
          </button>
        </>
      )}
    </div>
  );
}
