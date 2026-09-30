import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import { PageHeaderProvider, useHeaderState } from "./PageHeaderContext";

function AppShellContent() {
  const [collapsed, setCollapsed] = useState(false);
  const header = useHeaderState();

  return (
    <div className="flex h-screen w-full overflow-hidden bg-bg text-text-primary">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header title={header.title} breadcrumb={header.breadcrumb} actions={header.actions} />
        <main className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export function AppShell() {
  return (
    <PageHeaderProvider>
      <AppShellContent />
    </PageHeaderProvider>
  );
}
