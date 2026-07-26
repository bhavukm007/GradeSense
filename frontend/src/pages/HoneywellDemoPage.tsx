import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  CheckCircle2,
  ChevronDown,
  CircleGauge,
  Database,
  History,
  Lightbulb,
  Radio,
  ShieldCheck,
  Sparkles,
  Target,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { api } from '../api/client'
import type { ForecastRecommendation, RecommendationState } from '../api/types'
import { PageHeader } from '../components/ui/PageHeader'
import { Panel } from '../components/ui/Panel'
import { formatDate, formatNumber, formatPercent, labelize } from '../lib/format'

const requirements = [
  ['Predict off-spec Basis Weight', 'Sequential Forecasting'],
  ['Recommend safe setpoints', 'Forecast-backed Intervention Engine'],
  ['Reduce stabilization time', 'Counterfactual trajectory comparison'],
  ['Explain recommendations', 'Explainability + Inference Sources'],
  ['Discover new correlations', 'Lag, nonlinear, and interaction discovery'],
  ['Use recipe and historical evidence', 'Constraint attribution + lifecycle evidence'],
  ['Record operator responses', 'Recommendation Lifecycle'],
] as const

export function HoneywellDemoPage() {
  const client = useQueryClient()
  const [mappingOpen, setMappingOpen] = useState(true)
  const forecasts = useQuery({ queryKey: ['forecast-history'], queryFn: api.forecastHistory })
  const recommendations = useQuery({
    queryKey: ['intervention-history'],
    queryFn: api.interventionHistory,
  })
  const effectiveness = useQuery({
    queryKey: ['intervention-effectiveness'],
    queryFn: api.interventionEffectiveness,
  })
  const audit = useQuery({ queryKey: ['audit'], queryFn: api.adminAudit })
  const live = useQuery({ queryKey: ['live-metrics'], queryFn: api.liveMetrics })
  const discoveries = useQueries({
    queries: (['early', 'middle', 'late'] as const).map((stage) => ({
      queryKey: ['relationship-discovery', stage],
      queryFn: () => api.relationshipDiscovery(stage, 5),
    })),
  })
  const topDiscoveries = useMemo(
    () =>
      discoveries
        .flatMap((item) => item.data?.relationships ?? [])
        .sort((first, second) => second.strength - first.strength)
        .slice(0, 5),
    [discoveries],
  )
  const refresh = () => {
    void client.invalidateQueries()
  }
  const seed = useMutation({ mutationFn: api.seedDemo, onSuccess: refresh })
  const generate = useMutation({
    mutationFn: () =>
      api.generateInterventions({
        forecast_id: forecasts.data!.items[0].forecast_id,
        max_results: 5,
        max_variables: 2,
      }),
    onSuccess: refresh,
  })
  const decide = useMutation({
    mutationFn: ({
      recommendation,
      action,
    }: {
      recommendation: ForecastRecommendation
      action: 'accepted' | 'rejected' | 'applied'
    }) =>
      api.decideRecommendation(recommendation.recommendation_id, {
        operator_action: action,
        reason: 'Judge Workflow decision',
      }),
    onSuccess: refresh,
  })
  const evaluate = useMutation({
    mutationFn: (recommendation: ForecastRecommendation) =>
      api.evaluateRecommendationOutcome(recommendation.recommendation_id, {
        observations: recommendation.intervention_trajectory,
      }),
    onSuccess: refresh,
  })
  const forecast = forecasts.data?.items[0]
  const rows = recommendations.data ?? []
  const stabilization = [...rows].sort(
    (first, second) => stabilizationGain(second) - stabilizationGain(first),
  )

  return (
    <>
      <PageHeader
        eyebrow="Honeywell Round 2"
        title="Judge Workflow"
        description="One guided view from the current grade transition through prediction, evidence-backed action, operator response, and measured effectiveness."
      />
      <div className="mt-6 flex flex-wrap gap-3">
        <button
          onClick={() => seed.mutate()}
          disabled={seed.isPending}
          className="rounded-xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-ink-950"
        >
          {seed.isPending ? 'Preparing Demo Mode…' : 'Populate Demo Mode'}
        </button>
        {seed.data && (
          <p className="self-center text-sm text-emerald-500">
            Ready: {seed.data.predictions} predictions, {seed.data.recommendations} recommendations,{' '}
            {seed.data.outcomes} evaluated outcome.
          </p>
        )}
        {seed.error && <p className="self-center text-sm text-rose-500">{seed.error.message}</p>}
      </div>

      <Step number={1} title="Current transition" icon={Radio}>
        <div className="grid gap-3 sm:grid-cols-4">
          <Stat label="Transition" value={forecast?.transition_id ?? 'Waiting for forecast'} />
          <Stat
            label="Grade change"
            value={
              live.data?.sensor
                ? `${live.data.sensor.current_grade} → ${live.data.sensor.target_grade}`
                : 'Live replay starting'
            }
          />
          <Stat
            label="Current Basis Weight"
            value={
              live.data?.sensor ? formatNumber(live.data.sensor.basis_weight, 2) : 'Collecting'
            }
          />
          <Stat label="Model" value={forecast?.model_version ?? 'Not loaded'} />
        </div>
      </Step>

      <Step number={2} title="Future Basis Weight forecast" icon={CircleGauge}>
        {forecast ? (
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={forecast.trajectory}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                <XAxis dataKey="step" />
                <YAxis domain={['auto', 'auto']} />
                <Tooltip />
                <Legend />
                <Line
                  dataKey="basis_weight"
                  name="Future Basis Weight"
                  stroke="#22d3ee"
                  strokeWidth={3}
                />
                <Line dataKey="upper_spec_limit" name="+2.5% limit" stroke="#fb7185" dot={false} />
                <Line dataKey="lower_spec_limit" name="-2.5% limit" stroke="#fb7185" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <Empty>Use Demo Mode or wait for the live replay to persist a forecast.</Empty>
        )}
      </Step>

      <Step number={3} title="Off-spec prediction" icon={Target}>
        <div className="grid gap-3 sm:grid-cols-4">
          <Stat
            label="Crossing probability"
            value={formatPercent(forecast?.specification.crossing_probability ?? 0)}
          />
          <Stat
            label="Maximum deviation"
            value={`${formatNumber(forecast?.specification.maximum_predicted_deviation_pct ?? 0, 2)}%`}
          />
          <Stat
            label="Predicted crossing"
            value={
              forecast?.specification.predicted_crossing_step
                ? `Step ${forecast.specification.predicted_crossing_step}`
                : 'No crossing in horizon'
            }
          />
          <Stat label="Forecast confidence" value={formatPercent(forecast?.confidence ?? 0)} />
        </div>
        {forecast && <p className="mt-3 text-sm text-slate-500">{forecast.explanation}</p>}
      </Step>

      <Step number={4} title="Top discovered correlations" icon={Sparkles}>
        <div className="grid gap-3 lg:grid-cols-2">
          {topDiscoveries.map((item) => (
            <div
              key={`${item.stage}-${item.relationship_type}-${item.variable}-${item.interacts_with ?? ''}`}
              className="rounded-xl bg-slate-50 p-4 dark:bg-white/[0.04]"
            >
              <div className="flex justify-between gap-3">
                <b>
                  {labelize(item.variable)}
                  {item.interacts_with ? ` × ${labelize(item.interacts_with)}` : ' → Basis Weight'}
                </b>
                <Badge>{item.severity}</Badge>
              </div>
              <p className="mt-2 text-sm text-slate-500">{item.summary}</p>
              <p className="mt-2 text-xs font-semibold text-cyan-500">
                {item.relationship_type} · {item.stage} · {item.impact_direction} · strength{' '}
                {formatNumber(item.strength, 3)}
              </p>
            </div>
          ))}
        </div>
      </Step>

      <Step number={5} title="Ranked recommendations" icon={Lightbulb}>
        <button
          onClick={() => generate.mutate()}
          disabled={!forecast || generate.isPending}
          className="mb-4 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-ink-950"
        >
          Generate ranked recommendations
        </button>
        <div className="space-y-4">
          {rows.slice(0, 5).map((item) => (
            <RecommendationEvidence
              key={item.recommendation_id}
              item={item}
              deciding={decide.isPending}
              evaluating={evaluate.isPending}
              onDecision={(action) => decide.mutate({ recommendation: item, action })}
              onEvaluate={() => evaluate.mutate(item)}
            />
          ))}
          {!rows.length && <Empty>No recommendations yet.</Empty>}
        </div>
      </Step>

      <Step number={6} title="Inference source evidence" icon={Database}>
        <p className="text-sm text-slate-500">
          Each card above identifies whether the recommendation came from the forecast, historical
          trend, recipe constraint, correlation analysis, or a historically successful transition.
        </p>
      </Step>

      <Step number={7} title="Accept / Reject / Apply" icon={CheckCircle2}>
        <p className="text-sm text-slate-500">
          Use the action buttons on any recommendation above. Every response is persisted in the
          recommendation lifecycle.
        </p>
      </Step>

      <Step number={8} title="Outcome evaluation" icon={Target}>
        <p className="text-sm text-slate-500">
          Accepted or applied recommendations expose an Evaluate Outcome button. Demo evaluation
          submits the displayed intervention trajectory as the observed comparison.
        </p>
      </Step>

      <Step number={9} title="Historical effectiveness" icon={CircleGauge}>
        <div className="grid gap-3 sm:grid-cols-4">
          <Stat label="Evaluated" value={String(effectiveness.data?.evaluated_count ?? 0)} />
          <Stat
            label="Crossing avoidance"
            value={formatPercent(effectiveness.data?.crossing_avoidance_rate ?? 0)}
          />
          <Stat
            label="Deviation improvement"
            value={`${formatNumber(effectiveness.data?.mean_deviation_improvement ?? 0, 2)}%`}
          />
          <Stat
            label="Stabilization improvement"
            value={`${formatNumber(effectiveness.data?.mean_stabilization_improvement ?? 0, 1)} steps`}
          />
        </div>
      </Step>

      <Step number={10} title="Audit history" icon={History}>
        <div className="space-y-2">
          {(audit.data ?? []).slice(0, 8).map((entry) => (
            <div
              key={entry.audit_id}
              className="grid gap-1 rounded-xl bg-slate-50 p-3 text-sm dark:bg-white/[0.04] sm:grid-cols-3"
            >
              <span>{formatDate(entry.timestamp)}</span>
              <b>{entry.action}</b>
              <span>{entry.actor}</span>
            </div>
          ))}
        </div>
      </Step>

      <Panel className="mt-6" title="Stabilization Guidance">
        <div className="overflow-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="text-xs uppercase text-slate-500">
              <tr>
                <th className="py-3">Rank / variable</th>
                <th>Current</th>
                <th>Suggested</th>
                <th>Stabilization</th>
                <th>Deviation reduction</th>
                <th>Constraint</th>
                <th>Recipe rule</th>
                <th>Historical success</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-white/10">
              {stabilization.map((item) =>
                item.changes.map((change) => (
                  <tr key={`${item.recommendation_id}-${change.variable}`}>
                    <td className="py-3 font-semibold">
                      #{item.rank} {labelize(change.variable)}
                    </td>
                    <td>{formatNumber(item.current_values[change.variable] ?? 0, 2)}</td>
                    <td>{formatNumber(change.value, 2)}</td>
                    <td>{stabilizationGain(item)} steps</td>
                    <td>
                      {formatNumber(
                        item.metrics.predicted_peak_deviation_before -
                          item.metrics.predicted_peak_deviation_after,
                        2,
                      )}
                      %
                    </td>
                    <td>{item.constraint_validation.feasible ? 'Validated' : 'Blocked'}</td>
                    <td>{item.constraint_validation.recipe_rules[0] ?? 'Equipment limits'}</td>
                    <td>{formatPercent(item.historical_evidence.historical_effectiveness)}</td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
        </div>
      </Panel>

      <Panel className="mt-6">
        <button
          className="flex w-full items-center justify-between text-left font-semibold"
          onClick={() => setMappingOpen((open) => !open)}
        >
          How this satisfies the Honeywell Challenge
          <ChevronDown className={`size-5 transition ${mappingOpen ? 'rotate-180' : ''}`} />
        </button>
        {mappingOpen && (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {requirements.map(([requirement, implementation]) => (
              <div key={requirement} className="flex gap-3 rounded-xl bg-emerald-400/10 p-4">
                <ShieldCheck className="mt-0.5 size-5 shrink-0 text-emerald-500" />
                <div>
                  <p className="font-semibold">{requirement}</p>
                  <p className="mt-1 text-sm text-slate-500">Implemented by {implementation}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </>
  )
}

function RecommendationEvidence({
  item,
  deciding,
  evaluating,
  onDecision,
  onEvaluate,
}: {
  item: ForecastRecommendation
  deciding: boolean
  evaluating: boolean
  onDecision: (action: 'accepted' | 'rejected' | 'applied') => void
  onEvaluate: () => void
}) {
  return (
    <div className="rounded-2xl border border-slate-200 p-5 dark:border-white/10">
      <div className="flex flex-wrap justify-between gap-3">
        <div>
          <p className="font-semibold">
            #{item.rank}{' '}
            {item.changes
              .map((change) => `${labelize(change.variable)} → ${formatNumber(change.value, 2)}`)
              .join(', ')}
          </p>
          <p className="mt-1 text-sm text-slate-500">{item.explanation.selection_reason}</p>
        </div>
        <Badge>{item.state}</Badge>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {item.inference_sources.map((source) => (
          <Badge key={source}>{source}</Badge>
        ))}
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Stat
          label="Acceptance"
          value={formatPercent(item.historical_evidence.historical_acceptance_rate)}
        />
        <Stat
          label="Effectiveness"
          value={formatPercent(item.historical_evidence.historical_effectiveness)}
        />
        <Stat
          label="Similar transitions"
          value={String(item.historical_evidence.similar_transition_count)}
        />
        <Stat label="Forecast confidence" value={formatPercent(item.confidence)} />
        <Stat
          label="Crossing reduction"
          value={formatPercent(
            Math.max(
              item.metrics.crossing_probability_before - item.metrics.crossing_probability_after,
              0,
            ),
          )}
        />
        <Stat label="Stabilization gain" value={`${stabilizationGain(item)} steps`} />
      </div>
      <div className="mt-3 rounded-xl bg-slate-50 p-3 text-sm dark:bg-white/[0.04]">
        <p>{item.explanation.trajectory_effect}</p>
        <p className="mt-2 text-xs text-slate-500">
          Constraint: {item.constraint_validation.feasible ? 'validated' : 'blocked'} · Predicted
          improvement {formatPercent(item.metrics.estimated_improvement)}
        </p>
        <p className="mt-1 text-xs text-slate-500">
          Recipe: {item.explanation.recipe_attribution.join('; ') || 'Equipment operating limits'}
        </p>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {(['accepted', 'rejected', 'applied'] as const).map((action) => (
          <button
            key={action}
            disabled={deciding || item.state === 'evaluated'}
            onClick={() => onDecision(action)}
            className="rounded-lg bg-slate-100 px-3 py-2 text-xs font-semibold capitalize dark:bg-white/10"
          >
            {action}
          </button>
        ))}
        {(['accepted', 'applied'] as RecommendationState[]).includes(item.state) && (
          <button
            disabled={evaluating}
            onClick={onEvaluate}
            className="rounded-lg bg-cyan-500 px-3 py-2 text-xs font-semibold text-ink-950"
          >
            Evaluate Outcome
          </button>
        )}
      </div>
    </div>
  )
}

function Step({
  number,
  title,
  icon: Icon,
  children,
}: {
  number: number
  title: string
  icon: typeof Radio
  children: ReactNode
}) {
  return (
    <Panel className="mt-6">
      <div className="mb-4 flex items-center gap-3">
        <span className="grid size-9 place-items-center rounded-full bg-cyan-500 font-bold text-ink-950">
          {number}
        </span>
        <Icon className="size-5 text-cyan-500" />
        <h2 className="text-lg font-semibold">{title}</h2>
      </div>
      {children}
    </Panel>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3 dark:bg-white/[0.04]">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 font-semibold">{value}</p>
    </div>
  )
}

function Badge({ children }: { children: ReactNode }) {
  return (
    <span className="rounded-full bg-indigo-400/10 px-2.5 py-1 text-xs font-semibold text-indigo-500">
      {children}
    </span>
  )
}

function Empty({ children }: { children: ReactNode }) {
  return <p className="rounded-xl bg-slate-50 p-4 text-sm text-slate-500">{children}</p>
}

function stabilizationGain(item: ForecastRecommendation) {
  const before = item.metrics.predicted_stabilization_time_before
  const after = item.metrics.predicted_stabilization_time_after
  return before != null && after != null ? Math.max(before - after, 0) : 0
}
