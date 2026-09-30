import { NavLink } from "react-router-dom";
import { LayoutGrid, FolderGit2, Settings, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { UserMenu } from "./UserMenu";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Overview", icon: LayoutGrid },
  { to: "/repositories", label: "Repositories", icon: FolderGit2 },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <aside
      className={cn(
        "flex h-full flex-col border-r border-border bg-surface transition-[width] duration-200",
        collapsed ? "w-[68px]" : "w-60"
      )}
    >
      <div className="flex h-14 items-center gap-2.5 border-b border-border px-4">
        <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground">
          <span className="font-mono text-sm font-bold">CA</span>
        </div>
        {!collapsed && (
          <span className="truncate text-sm font-semibold tracking-tight text-text-primary">
            Code Archaeologist
          </span>
        )}
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 p-2.5" aria-label="Primary">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "focus-ring flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-surface-elevated text-text-primary"
                  : "text-text-secondary hover:bg-surface-elevated hover:text-text-primary"
              )
            }
            title={collapsed ? label : undefined}
          >
            <Icon className="size-4 shrink-0" aria-hidden="true" />
            {!collapsed && <span className="truncate">{label}</span>}
          </NavLink>
        ))}

        <div className="my-2 border-t border-border" />

        <button
          type="button"
          className="focus-ring flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm font-medium text-text-secondary transition-colors hover:bg-surface-elevated hover:text-text-primary"
          title={collapsed ? "Settings" : undefined}
        >
          <Settings className="size-4 shrink-0" aria-hidden="true" />
          {!collapsed && <span>Settings</span>}
        </button>
      </nav>

      <div className="border-t border-border p-2.5">
        <button
          type="button"
          onClick={onToggle}
          className="focus-ring mb-1 flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-sm text-text-muted transition-colors hover:bg-surface-elevated hover:text-text-primary"
        >
          {collapsed ? (
            <PanelLeftOpen className="size-4 shrink-0" aria-hidden="true" />
          ) : (
            <PanelLeftClose className="size-4 shrink-0" aria-hidden="true" />
          )}
          {!collapsed && <span>Collapse</span>}
        </button>
        <UserMenu collapsed={collapsed} />
      </div>
    </aside>
  );
}
