import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router'

import { AppLayout } from '../components/layout/AppLayout'
import { SkeletonGrid } from '../components/ui/QueryState'

const AnalyticsPage = lazy(() =>
  import('../pages/AnalyticsPage').then((module) => ({ default: module.AnalyticsPage })),
)
const CorrelationsPage = lazy(() =>
  import('../pages/CorrelationsPage').then((module) => ({ default: module.CorrelationsPage })),
)
const DashboardPage = lazy(() =>
  import('../pages/DashboardPage').then((module) => ({ default: module.DashboardPage })),
)
const DemoWorkspacePage = lazy(() =>
  import('../pages/DemoWorkspacePage').then((module) => ({
    default: module.DemoWorkspacePage,
  })),
)
const HistoryPage = lazy(() =>
  import('../pages/HistoryPage').then((module) => ({ default: module.HistoryPage })),
)
const ModelPage = lazy(() =>
  import('../pages/ModelPage').then((module) => ({ default: module.ModelPage })),
)
const NotFoundPage = lazy(() =>
  import('../pages/NotFoundPage').then((module) => ({ default: module.NotFoundPage })),
)
const PredictionPage = lazy(() =>
  import('../pages/PredictionPage').then((module) => ({ default: module.PredictionPage })),
)
const RecommendationHistoryPage = lazy(() =>
  import('../pages/RecommendationHistoryPage').then((module) => ({
    default: module.RecommendationHistoryPage,
  })),
)
const RecommendationsPage = lazy(() =>
  import('../pages/RecommendationsPage').then((module) => ({
    default: module.RecommendationsPage,
  })),
)
const SimulatorPage = lazy(() =>
  import('../pages/SimulatorPage').then((module) => ({ default: module.SimulatorPage })),
)
const SystemStatusPage = lazy(() =>
  import('../pages/SystemStatusPage').then((module) => ({ default: module.SystemStatusPage })),
)
const ModelRegistryPage = lazy(() =>
  import('../pages/AdminPages').then((module) => ({ default: module.ModelRegistryPage })),
)
const SystemMetricsPage = lazy(() =>
  import('../pages/AdminPages').then((module) => ({ default: module.SystemMetricsPage })),
)
const AuditLogPage = lazy(() =>
  import('../pages/AdminPages').then((module) => ({ default: module.AuditLogPage })),
)
const ConfigurationPage = lazy(() =>
  import('../pages/AdminPages').then((module) => ({ default: module.ConfigurationPage })),
)
const HealthDashboardPage = lazy(() =>
  import('../pages/AdminPages').then((module) => ({ default: module.HealthDashboardPage })),
)
const ExportCenterPage = lazy(() =>
  import('../pages/AdminPages').then((module) => ({ default: module.ExportCenterPage })),
)

export function App() {
  return (
    <Suspense
      fallback={
        <main className="p-8">
          <SkeletonGrid />
        </main>
      }
    >
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/demo-workspace" element={<DemoWorkspacePage />} />
          <Route path="/honeywell-demo" element={<Navigate to="/demo-workspace" replace />} />
          <Route path="/prediction" element={<PredictionPage />} />
          <Route path="/simulator" element={<SimulatorPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/correlations" element={<CorrelationsPage />} />
          <Route path="/recommendations" element={<RecommendationsPage />} />
          <Route path="/history/predictions" element={<HistoryPage />} />
          <Route path="/history/recommendations" element={<RecommendationHistoryPage />} />
          <Route path="/model" element={<ModelPage />} />
          <Route path="/status" element={<SystemStatusPage />} />
          <Route path="/admin/models" element={<ModelRegistryPage />} />
          <Route path="/admin/metrics" element={<SystemMetricsPage />} />
          <Route path="/admin/audit" element={<AuditLogPage />} />
          <Route path="/admin/config" element={<ConfigurationPage />} />
          <Route path="/admin/health" element={<HealthDashboardPage />} />
          <Route path="/admin/exports" element={<ExportCenterPage />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}
