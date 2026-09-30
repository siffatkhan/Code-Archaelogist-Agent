import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

interface PageHeaderState {
  title?: string;
  breadcrumb?: ReactNode;
  actions?: ReactNode;
}

interface PageHeaderContextValue {
  header: PageHeaderState;
  setHeader: (state: PageHeaderState) => void;
}

const PageHeaderContext = createContext<PageHeaderContextValue | undefined>(undefined);

export function PageHeaderProvider({ children }: { children: ReactNode }) {
  const [header, setHeader] = useState<PageHeaderState>({});
  return (
    <PageHeaderContext.Provider value={{ header, setHeader }}>{children}</PageHeaderContext.Provider>
  );
}

function usePageHeaderContext() {
  const ctx = useContext(PageHeaderContext);
  if (!ctx) throw new Error("usePageHeaderContext must be used within PageHeaderProvider");
  return ctx;
}

export function useHeaderState() {
  return usePageHeaderContext().header;
}

/**
 * Lets any page declare what the shared AppShell header should show.
 * Call once per page render; cleans itself up on unmount.
 */
export function usePageHeader(state: PageHeaderState, deps: unknown[] = []) {
  const { setHeader } = usePageHeaderContext();

  useEffect(() => {
    setHeader(state);
    return () => setHeader({});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
