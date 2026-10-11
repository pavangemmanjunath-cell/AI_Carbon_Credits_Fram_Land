import { lazy, Suspense, useEffect } from 'react';
import { Navigate, Route, Routes, useParams } from 'react-router';
import { useTranslation } from 'react-i18next';
import { AppShell } from '@/components/layout/AppShell';
import { PageSpinner } from '@/components/ui/PageSpinner';
import { useHealth } from '@/services/queries';
import { useUiStore } from '@/store/uiStore';

const LandingPage = lazy(() => import('@/features/landing/LandingPage'));
const WorkspacePage = lazy(() => import('@/features/workspace/WorkspacePage'));
const DataPage = lazy(() => import('@/features/data/DataPage'));
const AgentsPage = lazy(() => import('@/features/agents/AgentsPage'));
const TreeAgePage = lazy(() => import('@/features/tree-age/TreeAgePage'));
const ResultsPage = lazy(() => import('@/features/results/ResultsPage'));
const SimulatePage = lazy(() => import('@/features/simulate/SimulatePage'));
const ReportsPage = lazy(() => import('@/features/reports/ReportsPage'));
const ReportPage = lazy(() => import('@/features/report/ReportPage'));
const SpeciesPage = lazy(() => import('@/features/species/SpeciesPage'));
const SettingsPage = lazy(() => import('@/features/settings/SettingsPage'));

/** The 3D/4D cube views were removed; old links land on the plot's results page. */
function CubeRedirect() {
  const { id } = useParams();
  const selectedPlotId = useUiStore((s) => s.selectedPlotId);
  const plotId = id ?? selectedPlotId;
  return (
    <Navigate to={plotId ? `/app/plots/${encodeURIComponent(plotId)}/results` : '/app'} replace />
  );
}

export function App() {
  const { i18n } = useTranslation();
  const language = useUiStore((s) => s.language);
  useHealth();

  useEffect(() => {
    if (i18n.language !== language) void i18n.changeLanguage(language);
    document.documentElement.lang = language;
  }, [i18n, language]);

  return (
    <Suspense fallback={<PageSpinner />}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/app" element={<AppShell />}>
          <Route index element={<WorkspacePage />} />
          <Route path="data" element={<DataPage />} />
          <Route path="agents" element={<AgentsPage />} />
          <Route path="tree-age" element={<TreeAgePage />} />
          <Route path="simulate" element={<SimulatePage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="plots" element={<Navigate to="/app/data" replace />} />
          <Route path="plots/:id/results" element={<ResultsPage />} />
          <Route path="plots/:id/report" element={<ReportPage />} />
          <Route path="plots/:id/cube" element={<CubeRedirect />} />
          <Route path="cube" element={<CubeRedirect />} />
          <Route path="species" element={<SpeciesPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
