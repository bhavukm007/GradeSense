import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, AlertTriangle, CheckCircle2, Radio, Send } from 'lucide-react'
import { useState } from 'react'
import {
  CartesianGrid,
  Bar,
  BarChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { api } from '../../api/client'
import { useLiveStream } from '../../hooks/useLiveStream'
import { formatNumber, formatPercent, labelize } from '../../lib/format'
import { MetricCard } from '../ui/MetricCard'
import { Panel } from '../ui/Panel'

export function LiveMonitoring() {
  const { connected, live, status, trends, forecast, setLive } = useLiveStream()
  const queryClient = useQueryClient()
  const rolling = useQuery({
    queryKey: ['rolling-metrics'],
    queryFn: api.rollingMetrics,
    refetchInterval: 10_000,
  })
  const alerts = useQuery({
    queryKey: ['live-alerts'],
    queryFn: api.alerts,
    refetchInterval: 10_000,
  })
  const acknowledge = useMutation({
    mutationFn: api.acknowledgeAlert,
    onSuccess: (updated) => {
      setLive((current) => ({
        ...current,
        alerts: current.alerts.map((alert) => (alert.id === updated.id ? updated : alert)),
      }))
      void queryClient.invalidateQueries({ queryKey: ['live-alerts'] })
    },
  })
  const [outcome, setOutcome] = useState('recommendation_accepted')
  const [notes, setNotes] = useState('')
  const feedback = useMutation({
    mutationFn: api.createFeedback,
    onSuccess: () => setNotes(''),
  })
  const currentAlerts = [...live.alerts, ...(alerts.data ?? [])].filter(
    (alert, index, all) => all.findIndex((item) => item.id === alert.id) === index,
  )
  const latestWindow = rolling.data?.[0]

  return (
    <section className="mt-8 space-y-5" aria-label="Live process monitoring">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-4 dark:border-white/[0.08] dark:bg-ink-900">
        <div className="flex items-center gap-3">
          <span
            className={`size-3 rounded-full ${connected ? 'animate-pulse bg-emerald-400' : 'bg-rose-500'}`}
          />
          <div>
            <p className="text-sm font-semibold">
              {connected ? 'Live stream connected' : 'Reconnecting to live stream'}
            </p>
            <p className="text-xs text-slate-500">
              {status?.sample_count ?? 0} samples · {status?.connected_clients ?? 0} clients
            </p>
          </div>
        </div>
        <span className="rounded-full bg-cyan-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-cyan-500">
          {status?.status ?? 'starting'}
        </span>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          icon={Activity}
          label="Live Quality"
          value={live.prediction ? formatNumber(live.prediction.quality_score) : '—'}
          tone="emerald"
        />
        <MetricCard
          icon={AlertTriangle}
          label="Live Off-spec Risk"
          value={live.prediction ? formatPercent(live.prediction.off_spec_probability) : '—'}
          tone="rose"
        />
        <MetricCard
          icon={Radio}
          label="Stabilization"
          value={
            live.prediction
              ? `${formatNumber(live.prediction.expected_stabilization_time)} min`
              : '—'
          }
          tone="amber"
        />
        <MetricCard
          icon={live.drift?.severity === 'stable' ? CheckCircle2 : AlertTriangle}
          label="Model Drift PSI"
          value={live.drift ? formatNumber(live.drift.score, 3) : 'Collecting…'}
          detail={
            live.drift
              ? `${live.drift.severity} · ${Object.keys(live.drift.drifting_variables).length} variables`
              : 'Requires five samples'
          }
          tone={live.drift?.severity === 'stable' ? 'emerald' : 'amber'}
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <LiveChart
          title="Prediction trends"
          data={trends}
          series={[
            ['quality', '#34d399'],
            ['risk', '#fb7185'],
            ['stabilization', '#fbbf24'],
          ]}
        />
        <LiveChart
          title="Process variable trends"
          data={trends}
          series={[
            ['steamPressure', '#22d3ee'],
            ['moisture', '#818cf8'],
            ['temperature', '#f97316'],
            ['machineSpeed', '#a78bfa'],
          ]}
        />
      </div>

      {forecast && (
        <Panel title="Basis-weight forecast and specification envelope">
          <div className="mb-4 grid gap-3 sm:grid-cols-4">
            <Stat
              label="Crossing risk"
              value={formatPercent(forecast.specification.crossing_probability)}
            />
            <Stat
              label="Crossing time"
              value={
                forecast.specification.predicted_crossing_step
                  ? `Step ${forecast.specification.predicted_crossing_step}`
                  : 'No crossing'
              }
            />
            <Stat
              label="Safe time"
              value={
                forecast.specification.remaining_safe_operating_seconds == null
                  ? `>${forecast.forecast_horizon * 10}s`
                  : `${forecast.specification.remaining_safe_operating_seconds}s`
              }
            />
            <Stat
              label="Stabilization"
              value={
                forecast.specification.predicted_stabilization_step
                  ? `${forecast.specification.predicted_stabilization_step * 10}s`
                  : 'Beyond horizon'
              }
            />
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={forecast.trajectory}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                <XAxis dataKey="step" />
                <YAxis domain={['auto', 'auto']} />
                <Tooltip />
                <Legend />
                <Line dataKey="upper_bound" stroke="#64748b" strokeDasharray="4 4" dot={false} />
                <Line
                  dataKey="basis_weight"
                  name="Forecast basis weight"
                  stroke="#22d3ee"
                  strokeWidth={3}
                  dot={false}
                />
                <Line dataKey="lower_bound" stroke="#64748b" strokeDasharray="4 4" dot={false} />
                <Line dataKey="upper_spec_limit" name="+2.5% limit" stroke="#fb7185" dot={false} />
                <Line dataKey="lower_spec_limit" name="-2.5% limit" stroke="#fb7185" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-3 text-sm text-slate-500">{forecast.explanation}</p>
        </Panel>
      )}

      {live.sensor && (
        <Panel
          title={`Active Transition: ${live.sensor.current_grade} → ${live.sensor.target_grade}`}
        >
          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {Object.entries(live.sensor)
              .filter(([key]) => !key.includes('grade'))
              .map(([key, value]) => (
                <div key={key} className="rounded-xl bg-slate-50 p-3 dark:bg-white/[0.04]">
                  <p className="text-xs text-slate-500">{labelize(key)}</p>
                  <p className="mt-1 font-semibold">{formatNumber(Number(value), 2)}</p>
                </div>
              ))}
          </div>
        </Panel>
      )}

      <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <Panel title="Live alerts">
          <div className="max-h-96 space-y-3 overflow-auto">
            {currentAlerts.slice(0, 12).map((alert) => (
              <div
                key={alert.id}
                className={`rounded-xl border p-4 ${alert.severity === 'critical' ? 'border-rose-400/30 bg-rose-400/10' : 'border-amber-400/30 bg-amber-400/10'}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold">{alert.title}</p>
                    <p className="mt-1 text-sm opacity-80">{alert.description}</p>
                    <p className="mt-2 text-xs opacity-70">{alert.suggested_action}</p>
                  </div>
                  {alert.acknowledged ? (
                    <span className="text-xs font-semibold text-emerald-500">Acknowledged</span>
                  ) : (
                    <button
                      className="text-xs font-semibold text-cyan-500"
                      onClick={() => acknowledge.mutate(alert.id)}
                    >
                      Acknowledge
                    </button>
                  )}
                </div>
              </div>
            ))}
            {!currentAlerts.length && (
              <p className="text-sm text-slate-500">No live alerts have been raised.</p>
            )}
          </div>
        </Panel>
        <Panel title="Rolling metrics">
          {latestWindow ? (
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <Stat label="Window" value={latestWindow.window} />
              <Stat label="Predictions" value={String(latestWindow.prediction_count)} />
              <Stat label="Average quality" value={formatNumber(latestWindow.average_quality)} />
              <Stat
                label="Average risk"
                value={formatPercent(latestWindow.average_off_spec_probability)}
              />
              <Stat label="Recommendations" value={String(latestWindow.recommendation_frequency)} />
              <Stat label="Alerts" value={String(latestWindow.alert_frequency)} />
            </dl>
          ) : (
            <p className="text-sm text-slate-500">Collecting rolling statistics…</p>
          )}
        </Panel>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Alert timeline">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={currentAlerts
                  .slice(0, 30)
                  .reverse()
                  .map((alert) => ({
                    time: new Date(alert.timestamp).toLocaleTimeString(),
                    severity:
                      alert.severity === 'critical' ? 3 : alert.severity === 'warning' ? 2 : 1,
                  }))}
              >
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                <XAxis dataKey="time" tick={{ fontSize: 10 }} />
                <YAxis domain={[0, 3]} ticks={[1, 2, 3]} />
                <Tooltip />
                <Line dataKey="severity" stroke="#fb7185" isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Recommendation and alert frequency">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rolling.data ?? []}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                <XAxis dataKey="window" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="recommendation_frequency" fill="#2dd4bf" />
                <Bar dataKey="alert_frequency" fill="#fb7185" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Panel title="Current recommendations">
          <div className="space-y-3">
            {live.recommendations.map((recommendation) => (
              <div
                key={recommendation.text}
                className="rounded-xl bg-slate-50 p-4 dark:bg-white/[0.04]"
              >
                <p className="font-medium">{recommendation.text}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {formatPercent(recommendation.confidence)} confidence ·{' '}
                  {formatNumber(recommendation.expected_improvement)} improvement
                </p>
              </div>
            ))}
            {!live.recommendations.length && (
              <p className="text-sm text-slate-500">No beneficial intervention detected.</p>
            )}
          </div>
          {live.prediction && (
            <p className="mt-4 text-sm text-slate-500">{live.prediction.explanation.summary}</p>
          )}
        </Panel>
        <Panel title="Operator feedback">
          <form
            onSubmit={(event) => {
              event.preventDefault()
              if (live.prediction)
                feedback.mutate({
                  prediction_id: live.prediction.prediction_id,
                  outcome,
                  notes: notes || undefined,
                })
            }}
          >
            <select
              className="w-full rounded-xl border border-slate-300 bg-white p-3 text-sm dark:border-white/10 dark:bg-ink-900"
              value={outcome}
              onChange={(event) => setOutcome(event.target.value)}
            >
              <option value="recommendation_accepted">Recommendation accepted</option>
              <option value="recommendation_ignored">Recommendation ignored</option>
              <option value="recommendation_ineffective">Recommendation ineffective</option>
              <option value="problem_resolved">Problem resolved</option>
            </select>
            <textarea
              className="mt-3 min-h-24 w-full rounded-xl border border-slate-300 bg-white p-3 text-sm dark:border-white/10 dark:bg-ink-900"
              placeholder="Additional operator notes"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
            />
            <button
              disabled={!live.prediction || feedback.isPending}
              className="mt-3 inline-flex items-center gap-2 rounded-xl bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-ink-950 disabled:opacity-50"
            >
              <Send className="size-4" /> Submit feedback
            </button>
            {feedback.isSuccess && (
              <p className="mt-2 text-xs text-emerald-500">Feedback recorded.</p>
            )}
          </form>
        </Panel>
      </div>
    </section>
  )
}

function LiveChart({
  title,
  data,
  series,
}: {
  title: string
  data: object[]
  series: [string, string][]
}) {
  return (
    <Panel title={title}>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
            <XAxis dataKey="time" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            {series.map(([key, color]) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={color}
                dot={false}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-slate-500">{label}</dt>
      <dd className="mt-1 font-semibold">{value}</dd>
    </div>
  )
}
