import { useQuery } from '@tanstack/react-query'
import { Activity, Clock3, Database, Gauge, Server, ShieldAlert } from 'lucide-react'
import { Link } from 'react-router'

import { api } from '../api/client'
import { formatDate, formatNumber, formatPercent } from '../lib/format'
import { MetricCard } from '../components/ui/MetricCard'
import { PageHeader } from '../components/ui/PageHeader'
import { Panel } from '../components/ui/Panel'
import { ErrorState, SkeletonGrid } from '../components/ui/QueryState'
import { LiveMonitoring } from '../components/live/LiveMonitoring'

export function DashboardPage() {
  const model = useQuery({ queryKey: ['model'], queryFn: api.modelInfo, staleTime: 300_000 })
  const dataset = useQuery({
    queryKey: ['dataset-statistics'],
    queryFn: api.datasetStatistics,
    staleTime: 300_000,
  })
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, refetchInterval: 30_000 })
  const predictions = useQuery({
    queryKey: ['prediction-history', 1, 50],
    queryFn: () => api.predictionHistory(1, 50),
    refetchInterval: 30_000,
  })
  const recommendations = useQuery({
    queryKey: ['recommendation-history', 1, 5],
    queryFn: () => api.recommendationHistory(1, 5),
    refetchInterval: 30_000,
  })
  const loading = [model, dataset, predictions].some((query) => query.isLoading)
  const failed = [model, dataset, predictions].find((query) => query.error)
  const rows = predictions.data?.items ?? []
  const average = (selector: (row: (typeof rows)[number]) => number) =>
    rows.length ? rows.reduce((sum, row) => sum + selector(row), 0) / rows.length : 0

  return (
    <>
      <PageHeader
        eyebrow="Live operations"
        title="Transition command center"
        description="A real-time view of model readiness, transition predictions, and model-evaluated operator guidance."
      />
      <LiveMonitoring />
      {loading ? (
        <div className="mt-8">
          <SkeletonGrid count={6} />
        </div>
      ) : failed ? (
        <div className="mt-8">
          <ErrorState
            message={(failed.error as Error).message}
            onRetry={() => void failed.refetch()}
          />
        </div>
      ) : (
        <>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
            <MetricCard
              icon={Gauge}
              label="Model Version"
              value={model.data!.model_version.split('-').slice(0, 2).join('-')}
              detail={model.data!.model_type}
            />
            <MetricCard
              icon={Database}
              label="Dataset Size"
              value={formatNumber(dataset.data!.record_count, 0)}
              detail={`Generated ${formatDate(dataset.data!.generated_at)}`}
            />
            <MetricCard
              icon={Activity}
              label="Average Quality"
              value={rows.length ? formatNumber(average((row) => row.quality_score)) : '—'}
              tone="emerald"
              detail={`${rows.length} recent predictions`}
            />
            <MetricCard
              icon={ShieldAlert}
              label="Average Off-spec"
              value={rows.length ? formatPercent(average((row) => row.off_spec_probability)) : '—'}
              tone="rose"
            />
            <MetricCard
              icon={Clock3}
              label="Average Stabilization"
              value={
                rows.length
                  ? `${formatNumber(average((row) => row.expected_stabilization_time))} min`
                  : '—'
              }
              tone="amber"
            />
            <MetricCard
              icon={Server}
              label="Backend"
              value={health.isSuccess ? 'Connected' : 'Unavailable'}
              detail={
                health.data
                  ? `${health.data.service} · ${health.data.environment}`
                  : 'Connection check failed'
              }
              tone={health.isSuccess ? 'emerald' : 'rose'}
            />
          </div>
          <div className="mt-5 grid gap-5 xl:grid-cols-2">
            <Panel
              title="Latest prediction"
              action={
                <Link to="/prediction" className="text-sm font-semibold text-cyan-500">
                  New prediction →
                </Link>
              }
            >
              {rows[0] ? (
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <p className="text-xs text-slate-500">Quality</p>
                    <p className="mt-1 text-xl font-semibold">
                      {formatNumber(rows[0].quality_score)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Off-spec</p>
                    <p className="mt-1 text-xl font-semibold">
                      {formatPercent(rows[0].off_spec_probability)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Stabilization</p>
                    <p className="mt-1 text-xl font-semibold">
                      {formatNumber(rows[0].expected_stabilization_time)} min
                    </p>
                  </div>
                  <p className="col-span-3 mt-3 text-xs text-slate-500">
                    {formatDate(rows[0].created_at)} · {rows[0].input_data.current_grade} →{' '}
                    {rows[0].input_data.target_grade}
                  </p>
                </div>
              ) : (
                <p className="text-sm text-slate-500">No predictions have been recorded.</p>
              )}
            </Panel>
            <Panel
              title="Recent recommendations"
              action={
                <Link to="/recommendations" className="text-sm font-semibold text-cyan-500">
                  Open center →
                </Link>
              }
            >
              <div className="space-y-3">
                {(recommendations.data?.items ?? [])
                  .flatMap((item) => item.recommendations.slice(0, 1))
                  .slice(0, 4)
                  .map((item, index) => (
                    <div
                      key={`${item.text}-${index}`}
                      className="flex items-start gap-3 rounded-xl bg-slate-50 p-3 dark:bg-white/[0.04]"
                    >
                      <span className="mt-1.5 size-2 rounded-full bg-cyan-400" />
                      <div>
                        <p className="text-sm font-medium">{item.text}</p>
                        <p className="mt-1 text-xs text-slate-500">
                          {formatPercent(item.confidence)} confidence
                        </p>
                      </div>
                    </div>
                  ))}
                {!recommendations.data?.items.length && (
                  <p className="text-sm text-slate-500">No recommendations have been generated.</p>
                )}
              </div>
            </Panel>
          </div>
        </>
      )}
    </>
  )
}
