import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/features/auth/AuthContext";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { AppShell } from "@/components/layout/AppShell";
import { LoadingState } from "@/components/common/LoadingState";

const LoginPage = lazy(() => import("@/pages/LoginPage"));
const DashboardPage = lazy(() => import("@/pages/DashboardPage"));
const RepositoriesPage = lazy(() => import("@/pages/RepositoriesPage"));
const RepositoryPage = lazy(() => import("@/pages/RepositoryPage"));
const ExplorerPage = lazy(() => import("@/pages/ExplorerPage"));
const InsightsPage = lazy(() => import("@/pages/InsightsPage"));
const HistoryPage = lazy(() => import("@/pages/HistoryPage"));
const ArchitecturePage = lazy(() => import("@/pages/ArchitecturePage"));
const NotFoundPage = lazy(() => import("@/pages/NotFoundPage"));

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Suspense fallback={<LoadingState message="Loading..." className="min-h-screen" />}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            <Route
              element={
                <ProtectedRoute>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/repositories" element={<RepositoriesPage />} />
              <Route path="/repositories/:repositoryId" element={<RepositoryPage />} />
              <Route path="/repositories/:repositoryId/explorer" element={<ExplorerPage />} />
              <Route path="/repositories/:repositoryId/insights" element={<InsightsPage />} />
              <Route path="/repositories/:repositoryId/history" element={<HistoryPage />} />
              <Route path="/repositories/:repositoryId/architecture" element={<ArchitecturePage />} />
            </Route>

            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
}
