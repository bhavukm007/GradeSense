import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, CloudOff, Database, Server, Workflow } from 'lucide-react'

import { api } from '../api/client'
import { MetricCard } from '../components/ui/MetricCard'
import { PageHeader } from '../components/ui/PageHeader'
import { Panel } from '../components/ui/Panel'

export function SystemStatusPage() {
  const health = useQuery({
    queryKey: ['health'],
    queryFn: api.health,
    refetchInterval: 15_000,
    retry: 1,
  })
  const model = useQuery({ queryKey: ['model'], queryFn: api.modelInfo })
  const dataset = useQuery({ queryKey: ['dataset-statistics'], queryFn: api.datasetStatistics })
  const ready = health.isSuccess && model.isSuccess && dataset.isSuccess
  return (
    <>
      <PageHeader
        eyebrow="Platform operations"
        title="System status"
        description="Live connectivity and readiness checks for every service required by the operator dashboard."
      />
      <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          icon={health.isSuccess ? CheckCircle2 : CloudOff}
          label="Backend Connection"
          value={health.isLoading ? 'Checking…' : health.isSuccess ? 'Connected' : 'Unavailable'}
          tone={health.isSuccess ? 'emerald' : 'rose'}
        />
        <MetricCard
          icon={Server}
          label="API Service"
          value={health.data?.service ?? '—'}
          detail={health.data ? `v${health.data.version} · ${health.data.environment}` : undefined}
        />
        <MetricCard
          icon={Workflow}
          label="Model Artifact"
          value={model.isSuccess ? 'Ready' : model.isLoading ? 'Checking…' : 'Unavailable'}
          tone={model.isSuccess ? 'emerald' : 'rose'}
        />
        <MetricCard
          icon={Database}
          label="Dataset"
          value={
            dataset.isSuccess
              ? `${dataset.data.record_count.toLocaleString()} rows`
              : dataset.isLoading
                ? 'Checking…'
                : 'Unavailable'
          }
          tone={dataset.isSuccess ? 'emerald' : 'rose'}
        />
      </div>
      <Panel className="mt-5" title="Overall readiness">
        <div
          className={`flex items-center gap-3 rounded-xl p-4 ${ready ? 'bg-emerald-400/10 text-emerald-600' : 'bg-amber-400/10 text-amber-600'}`}
        >
          {ready ? <CheckCircle2 className="size-6" /> : <CloudOff className="size-6" />}
          <div>
            <p className="font-semibold">
              {ready ? 'All operator services are ready' : 'One or more services require attention'}
            </p>
            <p className="mt-1 text-sm opacity-80">
              Checks refresh automatically every 15 seconds.
            </p>
          </div>
        </div>
      </Panel>
    </>
  )
}
