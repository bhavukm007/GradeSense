import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import {
  CartesianGrid,
  Area,
  ComposedChart,
  Legend,
  Line,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { api } from '../../api/client'
import { formatPercent } from '../../lib/format'
import { Panel } from '../ui/Panel'

export function InterventionForecast() {
  const forecasts = useQuery({ queryKey: ['forecast-history'], queryFn: api.forecastHistory })
  const [variable, setVariable] = useState('stock_flow')
  const [value, setValue] = useState('')
  const simulation = useMutation({
    mutationFn: () =>
      api.simulateForecast({
        forecast_id: forecasts.data!.items[0].forecast_id,
        changes: [{ variable, value: Number(value) }],
      }),
  })
  const interventions = useMutation({
    mutationFn: () =>
      api.generateInterventions({
        forecast_id: forecasts.data!.items[0].forecast_id,
        max_results: 5,
        max_variables: 2,
      }),
  })
  const decision = useMutation({
    mutationFn: ({
      id,
      action,
    }: {
      id: string
      action: 'accepted' | 'rejected' | 'delayed' | 'applied'
    }) =>
      api.decideRecommendation(id, {
        operator_action: action,
        reason: 'Operator decision from recommendation comparison',
        delay_duration_seconds: action === 'delayed' ? 300 : undefined,
      }),
  })
  const latest = forecasts.data?.items[0]
  const chart = simulation.data?.baseline_trajectory.map((point, index) => ({
    step: point.step,
    baseline: point.basis_weight,
    intervention: simulation.data?.intervention_trajectory[index]?.basis_weight,
    baselineBand: [point.lower_bound, point.upper_bound],
    interventionBand: [
      simulation.data?.intervention_trajectory[index]?.lower_bound,
      simulation.data?.intervention_trajectory[index]?.upper_bound,
    ],
    upperSpec: point.upper_spec_limit,
    lowerSpec: point.lower_spec_limit,
  }))

  return (
    <Panel className="mt-5" title="Predictive intervention simulation">
      {!latest ? (
        <p className="text-sm text-slate-500">
          A persisted sequential forecast is required before an intervention can be simulated.
        </p>
      ) : (
        <>
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-semibold">Forecast-driven recommendation ranking</p>
              <p className="text-sm text-slate-500">
                Evaluates feasible one- and two-variable combinations with the forecasting model.
              </p>
            </div>
            <button
              onClick={() => interventions.mutate()}
              disabled={interventions.isPending}
              className="rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-ink-950"
            >
              {interventions.isPending ? 'Evaluating forecasts…' : 'Generate ranked actions'}
            </button>
          </div>
          {interventions.error && (
            <p className="mb-4 text-sm text-rose-500" role="alert">
              {interventions.error.message}
            </p>
          )}
          {interventions.isSuccess && interventions.data.length === 0 && (
            <p className="mb-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-500 dark:bg-white/[0.04]">
              No feasible intervention improved the current forecast.
            </p>
          )}
          {interventions.data?.map((item) => (
            <div
              key={item.recommendation_id}
              className="mb-4 rounded-xl border border-slate-200 p-4 dark:border-white/10"
            >
              <div className="flex flex-wrap justify-between gap-3">
                <div>
                  <p className="font-semibold">
                    #{item.rank}{' '}
                    {item.changes
                      .map(
                        (change) =>
                          `${change.variable.replaceAll('_', ' ')} → ${change.value.toFixed(2)}`,
                      )
                      .join(', ')}
                  </p>
                  <p className="mt-1 text-xs uppercase tracking-wide text-cyan-500">
                    {item.state} · {(item.confidence * 100).toFixed(1)}% confidence
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {(['accepted', 'rejected', 'delayed', 'applied'] as const).map((action) => (
                    <button
                      key={action}
                      onClick={() => decision.mutate({ id: item.recommendation_id, action })}
                      disabled={decision.isPending}
                      className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold capitalize dark:bg-white/10"
                    >
                      {action}
                    </button>
                  ))}
                </div>
              </div>
              <div className="mt-3 grid gap-2 sm:grid-cols-3">
                <Metric
                  label="Crossing probability"
                  value={`${formatPercent(item.metrics.crossing_probability_before)} → ${formatPercent(item.metrics.crossing_probability_after)}`}
                />
                <Metric
                  label="Peak deviation"
                  value={`${item.metrics.predicted_peak_deviation_before.toFixed(2)}% → ${item.metrics.predicted_peak_deviation_after.toFixed(2)}%`}
                />
                <Metric
                  label="Estimated improvement"
                  value={formatPercent(item.metrics.estimated_improvement)}
                />
              </div>
              <p className="mt-3 text-sm text-slate-500">{item.explanation.trajectory_effect}</p>
            </div>
          ))}
          <form
            className="flex flex-wrap items-end gap-3"
            onSubmit={(event) => {
              event.preventDefault()
              simulation.mutate()
            }}
          >
            <label className="text-sm">
              <span className="mb-1 block text-slate-500">Variable</span>
              <select
                className="rounded-xl border border-slate-300 bg-white p-2.5 dark:border-white/10 dark:bg-ink-900"
                value={variable}
                onChange={(event) => setVariable(event.target.value)}
              >
                {[
                  'stock_flow',
                  'filler_flow',
                  'steam_pressure',
                  'machine_speed',
                  'dryer_temperature',
                  'reel_tension',
                ].map((item) => (
                  <option key={item} value={item}>
                    {item.replaceAll('_', ' ')}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm">
              <span className="mb-1 block text-slate-500">Proposed setpoint</span>
              <input
                required
                type="number"
                step="any"
                value={value}
                onChange={(event) => setValue(event.target.value)}
                className="rounded-xl border border-slate-300 bg-white p-2.5 dark:border-white/10 dark:bg-ink-900"
              />
            </label>
            <button className="rounded-xl bg-cyan-500 px-4 py-2.5 text-sm font-semibold text-ink-950">
              {simulation.isPending ? 'Simulating…' : 'Simulate future'}
            </button>
          </form>
          {decision.isSuccess && (
            <p className="mt-3 text-sm text-emerald-500" role="status">
              Operator decision recorded.
            </p>
          )}
          {decision.error && (
            <p className="mt-3 text-sm text-rose-500" role="alert">
              {decision.error.message}
            </p>
          )}
          {simulation.error && (
            <p className="mt-3 text-sm text-rose-500">{simulation.error.message}</p>
          )}
          {simulation.data && (
            <>
              <div className="mt-5 grid gap-3 sm:grid-cols-3">
                <Metric
                  label="Risk reduction"
                  value={formatPercent(simulation.data.risk_reduction)}
                />
                <Metric
                  label="Deviation reduction"
                  value={`${simulation.data.expected_deviation_reduction.toFixed(2)}%`}
                />
                <Metric
                  label="Recommendation ID"
                  value={simulation.data.recommendation_id.slice(0, 8)}
                />
              </div>
              <div className="mt-4 h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chart}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                    <XAxis dataKey="step" />
                    <YAxis domain={['auto', 'auto']} />
                    <Tooltip />
                    <Legend />
                    <Area
                      dataKey="baselineBand"
                      name="Baseline confidence"
                      fill="#fb7185"
                      fillOpacity={0.1}
                      stroke="none"
                    />
                    <Area
                      dataKey="interventionBand"
                      name="Intervention confidence"
                      fill="#34d399"
                      fillOpacity={0.14}
                      stroke="none"
                    />
                    <Line dataKey="baseline" stroke="#fb7185" strokeWidth={2} dot={false} />
                    <Line dataKey="intervention" stroke="#34d399" strokeWidth={3} dot={false} />
                    <Line dataKey="upperSpec" stroke="#f59e0b" strokeDasharray="4 4" dot={false} />
                    <Line dataKey="lowerSpec" stroke="#f59e0b" strokeDasharray="4 4" dot={false} />
                    {simulation.data.baseline_trajectory
                      .filter((point) => Math.abs(point.deviation_pct) > 2.5)
                      .map((point) => (
                        <ReferenceDot
                          key={`crossing-${point.step}`}
                          x={point.step}
                          y={point.basis_weight}
                          r={4}
                          fill="#f43f5e"
                          stroke="white"
                          name="Baseline crossing"
                        />
                      ))}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-3 text-sm text-slate-500">{simulation.data.explanation}</p>
            </>
          )}
        </>
      )}
    </Panel>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3 dark:bg-white/[0.04]">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 font-semibold">{value}</p>
    </div>
  )
}
