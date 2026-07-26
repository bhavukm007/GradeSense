import { useQuery } from '@tanstack/react-query'
import { Binary, Boxes, CalendarClock, Database } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { api } from '../api/client'
import { MetricCard } from '../components/ui/MetricCard'
import { PageHeader } from '../components/ui/PageHeader'
import { Panel } from '../components/ui/Panel'
import { ErrorState, SkeletonGrid } from '../components/ui/QueryState'
import { formatDate, formatNumber, labelize } from '../lib/format'

export function ModelPage() {
  const query = useQuery({ queryKey: ['model'], queryFn: api.modelInfo, staleTime: 300_000 })
  if (query.isLoading)
    return (
      <>
        <PageHeader
          eyebrow="Model governance"
          title="Model information"
          description="Loading active model metadata…"
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
          eyebrow="Model governance"
          title="Model information"
          description="Active artifact details and measured training performance."
        />
        <div className="mt-8">
          <ErrorState message={query.error.message} />
        </div>
      </>
    )
  const data = query.data!
  const metrics = Object.entries(data.target_metrics).map(([name, value]) => ({
    name: labelize(name),
    value,
  }))
  return (
    <>
      <PageHeader
        eyebrow="Model governance"
        title="Model information"
        description="Traceability and measured training performance for the exact artifact currently serving predictions."
      />
      <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={Binary} label="Algorithm" value={data.model_type} />
        <MetricCard icon={Boxes} label="Feature Count" value={String(data.feature_count)} />
        <MetricCard
          icon={Database}
          label="Training Records"
          value={formatNumber(data.training_records, 0)}
        />
        <MetricCard icon={CalendarClock} label="Trained" value={formatDate(data.trained_at)} />
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <Panel title="Training metrics">
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={metrics} layout="vertical" margin={{ left: 55 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                <XAxis type="number" />
                <YAxis type="category" dataKey="name" width={170} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(value) => formatNumber(Number(value), 4)} />
                <Bar dataKey="value" fill="#2dd4bf" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Artifact details">
          <dl className="space-y-4 text-sm">
            <div>
              <dt className="text-slate-500">Model version</dt>
              <dd className="mt-1 break-all font-medium">{data.model_version}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Supported outputs</dt>
              <dd className="mt-1">{data.supported_outputs.map(labelize).join(', ')}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Dataset checksum</dt>
              <dd className="mt-1 break-all font-mono text-xs">{data.dataset_checksum}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Artifact location</dt>
              <dd className="mt-1 break-all font-mono text-xs">{data.artifact_path}</dd>
            </div>
          </dl>
        </Panel>
      </div>
    </>
  )
}
