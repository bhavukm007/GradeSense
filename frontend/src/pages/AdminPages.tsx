import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type { UseQueryResult } from '@tanstack/react-query'

import { api } from '../api/client'
import type { RuntimeConfig } from '../api/types'
import { formatDate, formatPercent } from '../lib/format'
import { PageHeader } from '../components/ui/PageHeader'
import { Panel } from '../components/ui/Panel'
import { ErrorState, SkeletonGrid } from '../components/ui/QueryState'

export function ModelRegistryPage() {
  const queryClient = useQueryClient()
  const query = useQuery({ queryKey: ['models'], queryFn: api.registeredModels })
  const promote = useMutation({
    mutationFn: api.promoteModel,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['models'] }),
  })
  const archive = useMutation({
    mutationFn: api.archiveModel,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['models'] }),
  })
  return (
    <AdminShell eyebrow="Production governance" title="Model Registry" query={query}>
      {(promote.error || archive.error) && (
        <p className="mb-4 rounded-xl bg-rose-500/10 p-3 text-sm text-rose-500" role="alert">
          {(promote.error ?? archive.error)?.message}
        </p>
      )}
      {(promote.isSuccess || archive.isSuccess) && (
        <p className="mb-4 rounded-xl bg-emerald-500/10 p-3 text-sm text-emerald-500" role="status">
          Model registry updated.
        </p>
      )}
      <div className="grid gap-4">
        {query.data?.map((model) => (
          <Panel key={model.model_id}>
            <div className="flex flex-wrap justify-between gap-4">
              <div>
                <p className="font-semibold">{model.name}</p>
                <p className="mt-1 text-sm text-slate-500">
                  {model.version} · {model.algorithm} · {model.model_kind}
                </p>
                <p className="mt-2 text-xs text-slate-500">
                  Registered {formatDate(model.created_at)}
                </p>
              </div>
              <div className="flex items-start gap-2">
                <Badge>{model.status}</Badge>
                {model.status !== 'active' && (
                  <button
                    className="rounded-lg bg-cyan-500 px-3 py-2 text-xs font-semibold text-ink-950"
                    onClick={() => promote.mutate(model.model_id)}
                  >
                    Promote
                  </button>
                )}
                {model.status === 'experimental' && (
                  <button
                    className="rounded-lg bg-slate-100 px-3 py-2 text-xs dark:bg-white/10"
                    onClick={() => archive.mutate(model.model_id)}
                  >
                    Archive
                  </button>
                )}
              </div>
            </div>
          </Panel>
        ))}
      </div>
    </AdminShell>
  )
}

export function SystemMetricsPage() {
  const query = useQuery({
    queryKey: ['admin-metrics'],
    queryFn: api.adminMetrics,
    refetchInterval: 5000,
  })
  const data = query.data
  return (
    <AdminShell eyebrow="Observability" title="System Metrics" query={query}>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="CPU" value={`${Number(data?.cpu_percent ?? 0).toFixed(1)}%`} />
        <Metric label="Memory" value={`${Number(data?.memory_percent ?? 0).toFixed(1)}%`} />
        <Metric
          label="Disk"
          value={formatPercent(
            Number(data?.disk_used_bytes ?? 0) / Math.max(Number(data?.disk_total_bytes ?? 1), 1),
          )}
        />
        <Metric label="Error rate" value={formatPercent(Number(data?.error_rate ?? 0))} />
        <Metric label="WebSockets" value={String(data?.active_websocket_connections ?? 0)} />
        <Metric label="Uptime" value={`${Number(data?.uptime_seconds ?? 0).toFixed(0)} s`} />
        <Metric label="Requests" value={String(data?.request_count ?? 0)} />
        <Metric label="Responses" value={String(data?.response_count ?? 0)} />
        <Metric label="Forecast throughput" value={String(data?.throughput?.forecast ?? 0)} />
        <Metric
          label="Recommendation throughput"
          value={String(data?.throughput?.recommendation ?? 0)}
        />
      </div>
      <Panel className="mt-5" title="Measured latency">
        <div className="grid gap-3 sm:grid-cols-3">
          {Object.entries(data?.latency ?? {}).map(([name, value]) => (
            <Panel key={name}>
              <p className="text-xs uppercase tracking-wide text-slate-500">{name}</p>
              <p className="mt-2 text-xl font-semibold">{Number(value.average_ms).toFixed(2)} ms</p>
              <div
                className="mt-3 flex h-10 items-end gap-0.5"
                aria-label={`${name} latency trend`}
              >
                {value.trend.slice(-30).map((point, index) => (
                  <span
                    key={`${point.timestamp}-${index}`}
                    className="min-w-0 flex-1 rounded-t bg-cyan-400/70"
                    style={{
                      height: `${Math.max(5, Math.min(100, (point.milliseconds / Math.max(value.latest_ms, value.average_ms, 1)) * 60))}%`,
                    }}
                  />
                ))}
              </div>
            </Panel>
          ))}
        </div>
      </Panel>
    </AdminShell>
  )
}

export function AuditLogPage() {
  const query = useQuery({ queryKey: ['audit'], queryFn: api.adminAudit })
  return (
    <AdminShell eyebrow="Immutable operations trail" title="Audit Log" query={query}>
      <Panel>
        <div className="space-y-2">
          {query.data?.map((entry) => (
            <div
              key={entry.audit_id}
              className="grid gap-1 rounded-xl bg-slate-50 p-3 text-sm dark:bg-white/[0.04] sm:grid-cols-4"
            >
              <span>{formatDate(entry.timestamp)}</span>
              <b>{entry.action}</b>
              <span>{entry.actor}</span>
              <span className="truncate">{entry.request_id ?? 'system'}</span>
            </div>
          ))}
        </div>
      </Panel>
    </AdminShell>
  )
}

export function ConfigurationPage() {
  const query = useQuery({ queryKey: ['admin-config'], queryFn: api.adminConfig })
  const [values, setValues] = useState<RuntimeConfig>()
  useEffect(() => {
    if (query.data) setValues(query.data)
  }, [query.data])
  const update = useMutation({ mutationFn: api.updateAdminConfig })
  return (
    <AdminShell eyebrow="Runtime controls" title="Configuration" query={query}>
      {update.isSuccess && (
        <p className="mb-4 text-sm text-emerald-500" role="status">
          Configuration reloaded.
        </p>
      )}
      {update.error && (
        <p className="mb-4 text-sm text-rose-500" role="alert">
          {update.error.message}
        </p>
      )}
      {values && (
        <Panel>
          <form
            className="grid gap-4 sm:grid-cols-2"
            onSubmit={(event) => {
              event.preventDefault()
              update.mutate(values)
            }}
          >
            {(
              [
                ['stream_speed_seconds', 'Stream speed'],
                ['forecast_horizon', 'Forecast horizon'],
                ['history_window', 'History window'],
                ['confidence_threshold', 'Confidence threshold'],
                ['relationship_threshold', 'Relationship threshold'],
                ['recommendation_limit', 'Recommendation limit'],
              ] as const
            ).map(([key, label]) => (
              <label key={key} className="text-sm">
                <span className="mb-1 block text-slate-500">{label}</span>
                <input
                  type="number"
                  step="any"
                  value={values[key]}
                  onChange={(event) => setValues({ ...values, [key]: Number(event.target.value) })}
                  className="w-full rounded-xl border border-slate-300 bg-white p-2.5 dark:border-white/10 dark:bg-ink-900"
                />
              </label>
            ))}
            <button className="rounded-xl bg-cyan-500 px-4 py-2.5 font-semibold text-ink-950 sm:col-span-2">
              Reload configuration
            </button>
          </form>
        </Panel>
      )}
    </AdminShell>
  )
}

export function HealthDashboardPage() {
  const query = useQuery({
    queryKey: ['admin-health'],
    queryFn: api.adminHealth,
    refetchInterval: 5000,
  })
  return (
    <AdminShell eyebrow="Production readiness" title="Health Dashboard" query={query}>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Object.entries(query.data?.checks ?? {}).map(([name, check]) => (
          <Panel key={name} title={name.replaceAll('_', ' ')}>
            <pre className="overflow-auto whitespace-pre-wrap text-xs text-slate-500">
              {JSON.stringify(check, null, 2)}
            </pre>
          </Panel>
        ))}
      </div>
    </AdminShell>
  )
}

export function ExportCenterPage() {
  const query = useQuery({ queryKey: ['exports'], queryFn: api.exportCatalog })
  const exportMutation = useMutation({
    mutationFn: ({ resource, format }: { resource: string; format: 'json' | 'csv' }) =>
      api.createExport(resource, format),
  })
  return (
    <AdminShell eyebrow="Operational portability" title="Export Center" query={query}>
      {exportMutation.isSuccess && (
        <p className="mb-4 text-sm text-emerald-500" role="status">
          Export downloaded.
        </p>
      )}
      {exportMutation.error && (
        <p className="mb-4 text-sm text-rose-500" role="alert">
          {exportMutation.error.message}
        </p>
      )}
      <Panel>
        <div className="space-y-2">
          {query.data?.map((item) => (
            <div
              key={item.resource}
              className="flex items-center justify-between rounded-xl bg-slate-50 p-3 dark:bg-white/[0.04]"
            >
              <span className="capitalize">
                {item.resource} <small className="text-slate-500">({item.row_count})</small>
              </span>
              <div className="flex gap-2">
                {(['json', 'csv'] as const).map((format) => (
                  <button
                    key={format}
                    disabled={exportMutation.isPending}
                    onClick={() => exportMutation.mutate({ resource: item.resource, format })}
                    className="rounded-lg bg-slate-200 px-3 py-1.5 text-xs font-semibold uppercase dark:bg-white/10"
                  >
                    {format}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </AdminShell>
  )
}

function AdminShell({
  eyebrow,
  title,
  query,
  children,
}: {
  eyebrow: string
  title: string
  query: UseQueryResult<unknown, Error>
  children: ReactNode
}) {
  return (
    <>
      <PageHeader
        eyebrow={eyebrow}
        title={title}
        description="Production operations and governance for GradeSenseAI."
      />
      {query.isLoading ? (
        <div className="mt-8">
          <SkeletonGrid />
        </div>
      ) : query.error ? (
        <div className="mt-8">
          <ErrorState message={query.error.message} />
        </div>
      ) : (
        <div className="mt-8">{children}</div>
      )}
    </>
  )
}
function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Panel>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </Panel>
  )
}
function Badge({ children }: { children: string }) {
  return (
    <span className="rounded-full bg-emerald-400/10 px-3 py-1 text-xs font-semibold uppercase text-emerald-500">
      {children}
    </span>
  )
}
