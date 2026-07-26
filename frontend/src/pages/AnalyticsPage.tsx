import { useQuery } from '@tanstack/react-query'
import { Database, Layers3, ListChecks, TriangleAlert } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { api } from '../api/client'
import { MetricCard } from '../components/ui/MetricCard'
import { PageHeader } from '../components/ui/PageHeader'
import { Panel } from '../components/ui/Panel'
import { ErrorState, SkeletonGrid } from '../components/ui/QueryState'
import { formatDate, formatNumber, labelize } from '../lib/format'

export function AnalyticsPage() {
  const query = useQuery({
    queryKey: ['dataset-statistics'],
    queryFn: api.datasetStatistics,
    staleTime: 300_000,
  })
  if (query.isLoading)
    return (
      <>
        <PageHeader
          eyebrow="Data intelligence"
          title="Dataset analytics"
          description="Loading dataset profile…"
        />
        <div className="mt-8">
          <SkeletonGrid />
        </div>
      </>
    )
  if (query.error)
    return (
      <>
        <PageHeader
          eyebrow="Data intelligence"
          title="Dataset analytics"
          description="Statistical profile of the active training dataset."
        />
        <div className="mt-8">
          <ErrorState message={query.error.message} onRetry={() => void query.refetch()} />
        </div>
      </>
    )
  const data = query.data!
  const grades = Object.entries(data.grade_distribution).map(([grade, count]) => ({ grade, count }))
  const missing = Object.values(data.missing_values).reduce((sum, value) => sum + value, 0)
  return (
    <>
      <PageHeader
        eyebrow="Data intelligence"
        title="Dataset analytics"
        description="Distribution, completeness, and process statistics from the exact dataset behind the active model."
      />
      <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          icon={Database}
          label="Records"
          value={formatNumber(data.record_count, 0)}
          detail={formatDate(data.generated_at)}
        />
        <MetricCard icon={Layers3} label="Variables" value={String(data.columns.length)} />
        <MetricCard
          icon={TriangleAlert}
          label="Missing Values"
          value={formatNumber(missing, 0)}
          tone={missing ? 'rose' : 'emerald'}
        />
        <MetricCard icon={ListChecks} label="Target Grades" value={String(grades.length)} />
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-[0.8fr_1.2fr]">
        <Panel title="Target grade distribution">
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={grades}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                <XAxis dataKey="grade" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#2dd4bf" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Variable statistics" className="overflow-hidden">
          <div className="max-h-[420px] overflow-auto">
            <table className="w-full min-w-[650px] text-left text-sm">
              <thead className="sticky top-0 bg-white text-xs uppercase text-slate-500 dark:bg-ink-900">
                <tr>
                  <th className="py-3">Variable</th>
                  <th>Mean</th>
                  <th>Median</th>
                  <th>Std dev</th>
                  <th>Minimum</th>
                  <th>Maximum</th>
                  <th>Missing</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-white/[0.06]">
                {Object.entries(data.numeric_summary).map(([name, summary]) => (
                  <tr key={name}>
                    <td className="py-3 font-medium">{labelize(name)}</td>
                    <td>{formatNumber(summary.mean, 2)}</td>
                    <td>{formatNumber(summary['50%'], 2)}</td>
                    <td>{formatNumber(summary.std, 2)}</td>
                    <td>{formatNumber(summary.min, 2)}</td>
                    <td>{formatNumber(summary.max, 2)}</td>
                    <td>{data.missing_values[name] ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </div>
    </>
  )
}
