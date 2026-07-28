import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  CheckCircle2,
  ChevronDown,
  CircleGauge,
  Database,
  History,
  Lightbulb,
  Radio,
  ShieldCheck,
  Target,
  TrendingDown,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
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
import { useRelationshipDiscoveries } from '../hooks/useRelationshipDiscoveries'
import { formatNumber, formatPercent, labelize } from '../lib/format'

const requirements = [
  ['Predict off-spec Basis Weight', 'Sequential Forecasting'],
  ['Recommend safe setpoints', 'Forecast-backed Intervention Engine'],
  ['Reduce stabilization time', 'Counterfactual trajectory comparison'],
  ['Explain recommendations', 'Explainability + Inference Sources'],
  ['Discover new correlations', 'Lag, nonlinear, and interaction discovery'],
  ['Use recipe and historical evidence', 'Constraint attribution + lifecycle evidence'],
  ['Record operator responses', 'Recommendation Lifecycle'],
] as const

const workflowStages = [
  'Current Process',
  'Sequential Forecast',
  'Transition Risk Prediction',
  'Ranked Operator Recommendations',
  'Inference Sources',
  'Accept / Reject / Apply',
  'Transition Effectiveness Summary',
  'Historical Effectiveness',
  'Operator Audit Trail',
  'Capability Coverage',
] as const

export function DemoWorkspacePage() {
  const client = useQueryClient()
  const [mappingOpen, setMappingOpen] = useState(true)
  const [activeStep, setActiveStep] = useState(1)
  const [actionFeedback, setActionFeedback] = useState<{
    recommendationId: string
    message: string
  }>()
  const health = useQuery({ queryKey: ['health'], queryFn: api.health })
  const forecasts = useQuery({ queryKey: ['forecast-history'], queryFn: api.forecastHistory })
  const recommendations = useQuery({
    queryKey: ['intervention-history'],
    queryFn: api.interventionHistory,
  })
  const effectiveness = useQuery({
    queryKey: ['intervention-effectiveness'],
    queryFn: api.interventionEffectiveness,
  })
  const auditEvents = useQuery({ queryKey: ['intervention-audit'], queryFn: api.interventionAudit })
  const live = useQuery({ queryKey: ['live-metrics'], queryFn: api.liveMetrics })
  const allCriticalEndpointsFailed = health.isError && forecasts.isError && live.isError
  const discoveries = useRelationshipDiscoveries(5)
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
        forecast_id: forecast!.forecast_id,
        max_results: 5,
        max_variables: 2,
      }),
    onSuccess: async (created) => {
      await client.cancelQueries({ queryKey: ['intervention-history'] })
      client.setQueryData<ForecastRecommendation[]>(['intervention-history'], (existing = []) => {
        const createdIds = new Set(created.map((item) => item.recommendation_id))
        return [...created, ...existing.filter((item) => !createdIds.has(item.recommendation_id))]
      })
      void client.invalidateQueries({ queryKey: ['intervention-effectiveness'] })
    },
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
        reason: 'Operator workflow decision',
      }),
    onSuccess: (_, variables) => {
      setActionFeedback({
        recommendationId: variables.recommendation.recommendation_id,
        message:
          variables.action === 'accepted'
            ? 'Recommendation Accepted'
            : variables.action === 'applied'
              ? 'Recommendation Applied'
              : 'Recommendation Rejected',
      })
      refresh()
    },
  })
  const evaluate = useMutation({
    mutationFn: (recommendation: ForecastRecommendation) =>
      api.evaluateRecommendationOutcome(recommendation.recommendation_id, {
        observations: recommendation.intervention_trajectory,
      }),
    onSuccess: (_, recommendation) => {
      setActionFeedback({
        recommendationId: recommendation.recommendation_id,
        message: 'Outcome Evaluated · Workflow Complete',
      })
      refresh()
    },
  })
  const recommendationForecastIds = new Set(
    (recommendations.data ?? []).map((item) => item.forecast_id),
  )
  const correlationVariables = useMemo(
    () =>
      new Set(
        topDiscoveries.flatMap((item) => [item.variable, ...(item.interacts_with ? [item.interacts_with] : [])]),
      ),
    [topDiscoveries],
  )
  const forecast =
    forecasts.data?.items.find(
      (item) =>
        item.transition_id.startsWith('DEMO-') &&
        recommendationForecastIds.has(item.forecast_id),
    ) ??
    forecasts.data?.items.find((item) => recommendationForecastIds.has(item.forecast_id)) ??
    forecasts.data?.items.find((item) => item.transition_id.startsWith('DEMO-')) ??
    forecasts.data?.items[0]
  const rows = useMemo(() => {
    const matching = (recommendations.data ?? []).filter(
      (item) => !forecast || item.forecast_id === forecast.forecast_id,
    )
    const latestByRank = new Map<number, ForecastRecommendation>()
    matching.forEach((item) => {
      const existing = latestByRank.get(item.rank)
      if (!existing || Date.parse(item.updated_at) > Date.parse(existing.updated_at)) {
        latestByRank.set(item.rank, item)
      }
    })
    return [...latestByRank.values()].sort((first, second) => first.rank - second.rank).slice(0, 5)
  }, [forecast, recommendations.data])
  const hasRecommendations = rows.length > 0
  const fatalGenerationError = generate.isError && !hasRecommendations
  const auxiliaryRecommendationWarning =
    recommendations.isError && !generate.isSuccess && !hasRecommendations
  const stabilization = rows
  const lifecycle = useMemo(() => {
    const accepted = rows.filter((item) =>
      ['accepted', 'applied', 'evaluated'].includes(item.state),
    ).length
    const rejected = rows.filter((item) => item.state === 'rejected').length
    const applied = rows.filter((item) => ['applied', 'evaluated'].includes(item.state)).length
    const evaluated = rows.filter((item) => item.state === 'evaluated').length
    const terminal = rows.filter((item) =>
      ['rejected', 'evaluated', 'expired'].includes(item.state),
    ).length
    const status =
      rows.length === 0
        ? 'Not started'
        : terminal === rows.length
          ? 'Complete'
          : rows.every((item) => item.state === 'proposed')
            ? 'Awaiting decisions'
            : 'In progress'
    return { accepted, rejected, applied, evaluated, status }
  }, [rows])
  const currentBasisWeight = live.data?.sensor?.basis_weight
  const chartData = useMemo(
    () =>
      (forecast?.trajectory ?? []).map((point) => ({
        ...point,
        current_basis_weight: currentBasisWeight,
        forecast_basis_weight: point.basis_weight,
      })),
    [currentBasisWeight, forecast?.trajectory],
  )

  useEffect(() => {
    const sections = workflowStages
      .map((_, index) => document.getElementById(`workflow-step-${index + 1}`))
      .filter((section): section is HTMLElement => Boolean(section))
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((first, second) => second.intersectionRatio - first.intersectionRatio)[0]
        if (visible) setActiveStep(Number(visible.target.id.replace('workflow-step-', '')))
      },
      { rootMargin: '-20% 0px -65% 0px', threshold: [0.05, 0.25, 0.5] },
    )
    sections.forEach((section) => observer.observe(section))
    const handleDocumentEnd = () => {
      if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 24) {
        setActiveStep(workflowStages.length)
      }
    }
    window.addEventListener('scroll', handleDocumentEnd, { passive: true })
    return () => {
      observer.disconnect()
      window.removeEventListener('scroll', handleDocumentEnd)
    }
  }, [])

  useEffect(() => {
    const activeStage = document.querySelector<HTMLElement>(
      '[aria-label="Operator decision workflow"] [aria-current="step"]',
    )
    activeStage?.scrollIntoView?.({ behavior: 'smooth', block: 'nearest', inline: 'nearest' })
  }, [activeStep])

  return (
    <>
      <PageHeader
        eyebrow="Industrial grade transition"
        title="Demo workspace"
        description="A guided operational view from the active process through forecast risk, evidence-backed action, operator response, and measured effectiveness."
      />
      <nav
        aria-label="Operator decision workflow"
        className="sticky top-20 z-20 mt-6 rounded-2xl border border-slate-200 bg-white/95 p-3 shadow-panel backdrop-blur-xl dark:border-white/[0.08] dark:bg-ink-900/95"
      >
        <ol className="workflow-steps grid grid-flow-col auto-cols-[minmax(9.5rem,1fr)] gap-1 overflow-x-auto pb-1 xl:auto-cols-[minmax(10.5rem,1fr)]">
          {workflowStages.map((stage, index) => (
            <li key={stage} className="min-w-0">
              <button
                type="button"
                aria-current={activeStep === index + 1 ? 'step' : undefined}
                onClick={() => {
                  setActiveStep(index + 1)
                  document
                    .getElementById(`workflow-step-${index + 1}`)
                    ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                  window.setTimeout(() => setActiveStep(index + 1), 700)
                }}
                className={`flex min-h-12 w-full items-center gap-2 rounded-xl px-2.5 text-left text-[11px] font-semibold leading-4 ${
                  activeStep === index + 1
                    ? 'bg-cyan-500/15 text-cyan-700 ring-1 ring-cyan-500/30 dark:text-cyan-300'
                    : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-white/5'
                }`}
              >
                <span
                  className={`grid size-6 shrink-0 place-items-center rounded-full text-[11px] ${
                    activeStep === index + 1
                      ? 'bg-cyan-500 text-ink-950'
                      : 'bg-slate-100 text-slate-500 dark:bg-white/10 dark:text-slate-300'
                  }`}
                >
                  {index + 1}
                </span>
                <span className="min-w-0 leading-4">{stage}</span>
              </button>
            </li>
          ))}
        </ol>
      </nav>
      <div className="mt-6 flex flex-wrap gap-3">
        <button
          onClick={() => seed.mutate()}
          disabled={seed.isPending}
          className="rounded-xl bg-cyan-500 px-5 py-2.5 text-sm font-semibold text-ink-950 shadow-sm hover:bg-cyan-400"
        >
          {seed.isPending ? 'Loading Scenario…' : 'Load Demo Scenario'}
        </button>
        {seed.data && (
          <p className="self-center text-sm text-emerald-500">
            Scenario Ready: {seed.data.predictions} predictions, {seed.data.recommendations}{' '}
            recommendations, {seed.data.outcomes} evaluated outcome.
          </p>
        )}
        {seed.error && (
          <p className="self-center text-sm text-amber-600 dark:text-amber-400">
            {allCriticalEndpointsFailed
              ? seed.error.message
              : 'The scenario refresh was delayed. Available demo data remains loaded; retry when ready.'}
          </p>
        )}
      </div>

      <Step number={1} title="Current Process" icon={Radio}>
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

      <Step number={2} title="Sequential Forecast" icon={CircleGauge}>
        {forecast ? (
          <div className="h-80 min-w-0">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 12, bottom: 4, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                <XAxis dataKey="step" tick={{ fontSize: 11 }} />
                <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11 }} width={42} />
                <Tooltip />
                <Legend iconType="line" wrapperStyle={{ paddingTop: 12, fontSize: 12 }} />
                <Line
                  dataKey="current_basis_weight"
                  name="Current trajectory"
                  stroke="#94a3b8"
                  strokeDasharray="5 5"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  dataKey="forecast_basis_weight"
                  name="Forecast trajectory"
                  stroke="#22d3ee"
                  strokeWidth={3}
                  activeDot={{ r: 5 }}
                />
                <Line
                  dataKey="upper_spec_limit"
                  name="Upper specification limit"
                  stroke="#fb7185"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  dataKey="lower_spec_limit"
                  name="Lower specification limit"
                  stroke="#fb7185"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <Empty>Load a demo scenario or wait for the live replay to persist a forecast.</Empty>
        )}
      </Step>

      <Step number={3} title="Transition Risk Prediction" icon={Target}>
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
          <ConfidenceStat label="Forecast confidence" value={forecast?.confidence ?? 0} />
        </div>
        {forecast && <p className="mt-3 text-sm text-slate-500">{forecast.explanation}</p>}
      </Step>

      <Step number={4} title="Ranked Operator Recommendations" icon={Lightbulb}>
        <button
          onClick={() => generate.mutate()}
          disabled={!forecast || generate.isPending}
          className="mb-4 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-ink-950 shadow-sm hover:bg-emerald-400"
        >
          {generate.isPending
            ? 'Ranking interventions and validating recipe constraints…'
            : 'Generate ranked recommendations'}
        </button>
        {fatalGenerationError && (
          <p className="mb-4 text-sm text-rose-500" role="alert">
            {generate.error?.message}
          </p>
        )}
        {generate.isError && hasRecommendations && (
          <p className="mb-4 text-xs text-amber-600 dark:text-amber-400" role="status">
            The recommendation refresh was delayed. Showing the available ranked recommendations.
          </p>
        )}
        {auxiliaryRecommendationWarning && (
          <p className="mb-4 text-xs text-amber-600 dark:text-amber-400" role="status">
            Saved recommendation history is temporarily unavailable. You can still generate new
            recommendations.
          </p>
        )}
        {generate.isSuccess && generate.data.length === 0 && (
          <p className="mb-4 text-sm text-amber-600 dark:text-amber-400" role="status">
            No feasible recommendation improved this forecast.
          </p>
        )}
        <div className="space-y-4">
          {generate.isPending && <RecommendationSkeletons />}
          {rows.slice(0, 5).map((item) => (
            <RecommendationEvidence
              key={item.recommendation_id}
              item={item}
              highlighted={item.rank === 1}
              deciding={decide.isPending}
              evaluating={evaluate.isPending}
              feedback={
                actionFeedback?.recommendationId === item.recommendation_id
                  ? actionFeedback.message
                  : undefined
              }
              onDecision={(action) => decide.mutate({ recommendation: item, action })}
              onEvaluate={() => evaluate.mutate(item)}
              correlationVariables={correlationVariables}
            />
          ))}
          {!rows.length && !fatalGenerationError && !auxiliaryRecommendationWarning && (
            <Empty>No recommendations yet.</Empty>
          )}
        </div>
      </Step>

      <Step number={5} title="Inference Sources" icon={Database}>
        <p className="text-sm text-slate-500">
          Each card above identifies whether the recommendation came from the forecast, historical
          trend, recipe constraint, correlation analysis, or a historically successful transition.
        </p>
        <div className="mt-4 grid gap-3 lg:grid-cols-2">
          {topDiscoveries.map((item) => (
            <div
              key={`${item.stage}-${item.relationship_type}-${item.variable}-${item.interacts_with ?? ''}`}
              className="rounded-xl bg-slate-50 p-4 dark:bg-white/[0.04]"
            >
              <div className="flex flex-wrap justify-between gap-3">
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
          {!topDiscoveries.length && (
            <Empty>Relationship evidence will appear when transition analysis is available.</Empty>
          )}
        </div>
      </Step>

      <Step number={6} title="Accept / Reject / Apply" icon={CheckCircle2}>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {rows.map((item) => (
            <WorkflowStatus key={item.recommendation_id} item={item} />
          ))}
          {!rows.length && <Empty>Generate recommendations to begin the operator workflow.</Empty>}
        </div>
      </Step>

      <Step number={7} title="Transition Effectiveness Summary" icon={Target}>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Stat label="Accepted" value={String(lifecycle.accepted)} />
          <Stat label="Rejected" value={String(lifecycle.rejected)} />
          <Stat label="Applied" value={String(lifecycle.applied)} />
          <Stat label="Evaluated" value={String(lifecycle.evaluated)} />
          <Stat label="Workflow status" value={lifecycle.status} />
        </div>
      </Step>

      <Step number={8} title="Historical Effectiveness" icon={CircleGauge}>
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

      <Step number={9} title="Operator Audit Trail" icon={History}>
        <div className="space-y-2">
          {(auditEvents.data ?? []).map((event) => (
            <div
              key={`${event.recommendation_id}-${event.event}-${event.timestamp}`}
              className="grid items-start gap-3 rounded-xl bg-slate-50 p-3 text-sm dark:bg-white/[0.04] sm:grid-cols-[auto_1fr]"
            >
              <span className="rounded-full bg-cyan-500/10 px-2 py-1 text-xs font-bold text-cyan-600 dark:text-cyan-400">
                {formatTime(event.timestamp)}
              </span>
              <div>
                <b>{event.event}</b>
                <p className="mt-1 text-xs text-slate-500">{event.summary}</p>
              </div>
            </div>
          ))}
          {auditEvents.isLoading && <Empty>Loading recorded operator actions…</Empty>}
          {!auditEvents.isLoading && !auditEvents.data?.length && (
            <Empty>No recorded operator actions yet.</Empty>
          )}
        </div>
      </Step>

      <Panel className="mt-6" title="Stabilization Guidance">
        <div className="overflow-auto">
          <table className="w-full min-w-[680px] text-left text-sm">
            <caption className="sr-only">
              Essential setpoint guidance with expandable supporting evidence
            </caption>
            <thead className="text-xs uppercase text-slate-500">
              <tr>
                <th className="py-3">Variable</th>
                <th>Current</th>
                <th>Suggested</th>
                <th>Improvement</th>
                <th>Evidence</th>
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
                    <td>
                      <span className="inline-flex items-center gap-1 font-semibold text-emerald-600 dark:text-emerald-400">
                        <TrendingDown className="size-4" />
                        {formatPercent(item.metrics.estimated_improvement)}
                      </span>
                    </td>
                    <td>
                      <details>
                        <summary className="cursor-pointer font-semibold text-cyan-600 hover:text-cyan-500 dark:text-cyan-400">
                          View details
                        </summary>
                        <div className="mt-2 min-w-64 space-y-1 rounded-lg bg-slate-50 p-3 text-xs text-slate-600 dark:bg-white/[0.04] dark:text-slate-300">
                          <p>
                            Constraint:{' '}
                            {item.constraint_validation.feasible ? 'Validated' : 'Blocked'}
                          </p>
                          <p>
                            Recipe:{' '}
                            {item.constraint_validation.recipe_rules.join('; ') ||
                              'Equipment operating limits'}
                          </p>
                          <p>
                            Historical effectiveness:{' '}
                            {formatPercent(item.historical_evidence.historical_effectiveness)}
                          </p>
                          <p>Similar transitions: {item.historical_evidence.similar_transition_count}</p>
                        </div>
                      </details>
                    </td>
                  </tr>
                )),
              )}
            </tbody>
          </table>
          {!stabilization.length && (
            <div className="min-w-[680px] py-3">
              <Empty>Generate recommendations to view stabilization guidance.</Empty>
            </div>
          )}
        </div>
      </Panel>

      <Step number={10} title="Capability Coverage" icon={ShieldCheck}>
        <button
          className="flex w-full items-center justify-between text-left font-semibold"
          onClick={() => setMappingOpen((open) => !open)}
          aria-expanded={mappingOpen}
        >
          View platform evidence
          <ChevronDown className={`size-5 transition ${mappingOpen ? 'rotate-180' : ''}`} />
        </button>
        {mappingOpen && (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {requirements.map(([requirement, implementation]) => (
              <div key={requirement} className="flex gap-3 rounded-xl bg-emerald-400/10 p-4">
                <ShieldCheck className="mt-0.5 size-5 shrink-0 text-emerald-500" />
                <div>
                  <p className="font-semibold">{requirement}</p>
                  <p className="mt-1 text-sm text-slate-500">Evidence: {implementation}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Step>
    </>
  )
}

function RecommendationEvidence({
  item,
  highlighted,
  deciding,
  evaluating,
  feedback,
  onDecision,
  onEvaluate,
  correlationVariables,
}: {
  item: ForecastRecommendation
  highlighted: boolean
  deciding: boolean
  evaluating: boolean
  feedback?: string
  onDecision: (action: 'accepted' | 'rejected' | 'applied') => void
  onEvaluate: () => void
  correlationVariables: Set<string>
}) {
  const sources = visibleInferenceSources(item, correlationVariables)
  return (
    <article
      className={`relative overflow-hidden rounded-2xl border p-5 transition ${
        highlighted
          ? 'border-cyan-400/60 bg-cyan-500/[0.04] shadow-lg shadow-cyan-950/5 ring-1 ring-cyan-400/20 dark:bg-cyan-400/[0.04]'
          : 'border-slate-200 bg-white dark:border-white/10 dark:bg-ink-900'
      }`}
    >
      {highlighted && (
        <div className="absolute right-0 top-0 rounded-bl-xl bg-cyan-500 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-ink-950">
          Highest ranked
        </div>
      )}
      <div className="flex flex-wrap justify-between gap-3">
        <div className={highlighted ? 'pr-0 sm:pr-28' : ''}>
          <p className="text-base font-semibold">
            #{item.rank}{' '}
            {item.changes
              .map((change) => `${labelize(change.variable)} → ${formatNumber(change.value, 2)}`)
              .join(', ')}
          </p>
          <p className="mt-1 text-sm text-slate-500">{item.explanation.selection_reason}</p>
        </div>
        {!highlighted && item.state !== 'evaluated' && <StatusBadge state={item.state} />}
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {sources.map((source) => (
          <Badge key={source}>{source}</Badge>
        ))}
      </div>
      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        <ComparisonMetric
          label="Crossing probability"
          before={formatRiskProbability(item.metrics.crossing_probability_before, item.metrics.crossing_probability_after)}
          after={formatRiskProbability(item.metrics.crossing_probability_after, item.metrics.crossing_probability_before)}
          improved={item.metrics.crossing_probability_after < item.metrics.crossing_probability_before}
          improvement={crossingRiskChange(item)}
        />
        <ComparisonMetric
          label="Peak deviation"
          before={`${formatNumber(item.metrics.predicted_peak_deviation_before, 2)}%`}
          after={`${formatNumber(item.metrics.predicted_peak_deviation_after, 2)}%`}
          improved={
            item.metrics.predicted_peak_deviation_after <
            item.metrics.predicted_peak_deviation_before
          }
          improvement={peakDeviationImprovement(item)}
        />
        <ComparisonMetric
          label="Stabilization time"
          before={formatSteps(item.metrics.predicted_stabilization_time_before)}
          after={formatSteps(item.metrics.predicted_stabilization_time_after)}
          improved={stabilizationGain(item) > 0}
          improvement={stabilizationImprovement(item)}
          unavailable={
            item.metrics.predicted_stabilization_time_before == null ||
            item.metrics.predicted_stabilization_time_after == null
          }
        />
      </div>
      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
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
        <ConfidenceStat label="Forecast confidence" value={item.confidence} />
        <Stat
          label="Crossing-risk change"
          value={crossingRiskChange(item)}
        />
        <Stat label="Stabilization gain" value={stabilizationGainLabel(item)} />
      </div>
      <div className="mt-3 rounded-xl bg-slate-50 p-3 text-sm dark:bg-white/[0.04]">
        <p className="font-semibold">Expected effect</p>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-slate-600 dark:text-slate-300">
          <li>Crossing probability: {crossingRiskChange(item)}.</li>
          <li>Peak deviation: {peakDeviationImprovement(item)}.</li>
          <li>Stabilization: {stabilizationImprovement(item)}.</li>
          <li>Constraint validation {item.constraint_validation.feasible ? 'passed' : 'blocked'}.</li>
          <li>Similar successful transitions: {item.historical_evidence.similar_transition_count}.</li>
        </ul>
        <div className="hidden">
        <p className="mt-2 text-xs text-slate-500">
          Constraint: {item.constraint_validation.feasible ? 'validated' : 'blocked'} · Predicted
          improvement {formatPercent(item.metrics.estimated_improvement)}
        </p>
        <p className="mt-1">
          Recipe: {item.explanation.recipe_attribution.join('; ') || 'Equipment operating limits'}
        </p>
        </div>
      </div>
      {feedback && (
        <div
          className="mt-4 animate-[pulse_800ms_ease-out_1] rounded-xl bg-emerald-500/10 px-4 py-3 text-sm font-semibold text-emerald-600 dark:text-emerald-400"
          role="status"
        >
          ✓ {feedback}
        </div>
      )}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        {item.state === 'proposed' && (
          <>
            <button
              disabled={deciding}
              onClick={() => onDecision('accepted')}
              className="rounded-lg bg-cyan-500 px-4 py-2 text-xs font-semibold text-ink-950 hover:bg-cyan-400"
            >
              Accept
            </button>
            <button
              disabled={deciding}
              onClick={() => onDecision('rejected')}
              className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 dark:border-white/15 dark:bg-white/5 dark:text-slate-200"
            >
              Reject
            </button>
          </>
        )}
        {item.state === 'accepted' && (
          <button
            disabled={deciding}
            onClick={() => onDecision('applied')}
            className="rounded-lg bg-emerald-500 px-4 py-2 text-xs font-semibold text-ink-950 hover:bg-emerald-400"
          >
            Apply Recommendation
          </button>
        )}
        {item.state === 'applied' && (
          <button
            disabled={evaluating}
            onClick={onEvaluate}
            className="rounded-lg bg-cyan-500 px-3 py-2 text-xs font-semibold text-ink-950"
          >
            Evaluate Outcome
          </button>
        )}
        {item.state === 'evaluated' && (
          <StatusBadge state="evaluated" />
        )}
        {item.state === 'rejected' && <StatusBadge state="rejected" />}
      </div>
    </article>
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
    <Panel className="mt-6 scroll-mt-44" id={`workflow-step-${number}`}>
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

function ComparisonMetric({
  label,
  before,
  after,
  improved,
  improvement,
  unavailable = false,
}: {
  label: string
  before: string
  after: string
  improved: boolean
  improvement: string
  unavailable?: boolean
}) {
  return (
    <div className="rounded-xl border border-slate-200/80 bg-slate-50 p-3 dark:border-white/[0.06] dark:bg-white/[0.04]">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      {unavailable ? (
        <p className="mt-2 text-sm font-medium text-slate-500">Insufficient historical evidence</p>
      ) : (
        <dl className="mt-2 grid grid-cols-3 gap-2 text-xs">
          <div><dt className="text-slate-500">Current</dt><dd className="mt-1 font-semibold">{before}</dd></div>
          <div><dt className="text-slate-500">Predicted</dt><dd className="mt-1 font-semibold">{after}</dd></div>
          <div><dt className="text-slate-500">Improvement</dt><dd className={`mt-1 font-semibold ${improved ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-700 dark:text-slate-200'}`}>{improvement}</dd></div>
        </dl>
      )}
      <div className="hidden">
        <span className="text-sm text-slate-500 line-through decoration-slate-400/60">{before}</span>
        <span aria-hidden="true" className="text-slate-400">
          →
        </span>
        <span
          className={`font-semibold ${
            improved ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-900 dark:text-white'
          }`}
        >
          {after}
        </span>
        {improved && (
          <span className="ml-auto rounded-full bg-emerald-500/10 px-2 py-1 text-[10px] font-bold uppercase text-emerald-600 dark:text-emerald-400">
            Improved
          </span>
        )}
      </div>
    </div>
  )
}

function ConfidenceStat({ label, value }: { label: string; value: number }) {
  const level = value >= 0.8 ? 'High' : value >= 0.6 ? 'Medium' : 'Low'
  const tone =
    level === 'High'
      ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
      : level === 'Medium'
        ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
        : 'bg-rose-500/10 text-rose-600 dark:text-rose-400'
  return (
    <div className="rounded-xl bg-slate-50 p-3 dark:bg-white/[0.04]">
      <p className="text-xs text-slate-500">{label}</p>
      <div className="mt-1 flex flex-wrap items-center gap-2">
        <p className="font-semibold">{formatPercent(value, 0)}</p>
        <span className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase ${tone}`}>
          {level}
        </span>
      </div>
      {value < 0.3 && (
        <p className="mt-1 text-[11px] text-slate-500">Limited similar historical transitions.</p>
      )}
    </div>
  )
}

function WorkflowStatus({ item }: { item: ForecastRecommendation }) {
  const label =
    item.state === 'proposed'
      ? 'Awaiting decision'
      : item.state === 'accepted'
        ? 'Accepted'
        : item.state === 'applied'
          ? 'Applied'
          : item.state === 'evaluated'
            ? 'Workflow completed'
            : labelize(item.state)
  return (
    <div className="rounded-xl border border-slate-200 p-3 dark:border-white/10">
      <div className="flex items-center justify-between gap-2">
        <b>#{item.rank}</b>
        <StatusBadge state={item.state} />
      </div>
      <p className="mt-2 text-xs text-slate-500">{label}</p>
    </div>
  )
}

function StatusBadge({ state }: { state: RecommendationState }) {
  const complete = state === 'evaluated'
  const positive = state === 'accepted' || state === 'applied'
  const rejected = state === 'rejected'
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${
        complete || positive
          ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
          : rejected
            ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400'
            : 'bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-300'
      }`}
    >
      {complete ? '✓ Workflow Completed' : labelize(state)}
    </span>
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

function crossingRiskChange(item: ForecastRecommendation) {
  const percentagePoints =
    (item.metrics.crossing_probability_after - item.metrics.crossing_probability_before) * 100
  if (Math.abs(percentagePoints) < 0.005) return 'No measurable change'
  const direction = percentagePoints < 0 ? 'Reduced' : 'Increased'
  return `${direction} ${formatNumber(Math.abs(percentagePoints), 2)} pp`
}

function formatRiskProbability(value: number, comparison: number) {
  const oneDecimalMatches = Math.round(value * 1000) === Math.round(comparison * 1000)
  return formatPercent(value, oneDecimalMatches ? 3 : 2)
}

function peakDeviationImprovement(item: ForecastRecommendation) {
  const before = item.metrics.predicted_peak_deviation_before
  const after = item.metrics.predicted_peak_deviation_after
  if (before <= 0) return 'No measurable improvement'
  const improvement = ((before - after) / before) * 100
  return improvement > 0.005
    ? `${formatNumber(improvement, 1)}% reduction`
    : 'No measurable improvement'
}

function stabilizationImprovement(item: ForecastRecommendation) {
  const before = item.metrics.predicted_stabilization_time_before
  const after = item.metrics.predicted_stabilization_time_after
  if (before == null || after == null) return 'Insufficient historical evidence'
  const improvement = before - after
  return improvement > 0 ? `${formatNumber(improvement, 0)} steps faster` : 'No measurable improvement'
}

function stabilizationGainLabel(item: ForecastRecommendation) {
  const before = item.metrics.predicted_stabilization_time_before
  const after = item.metrics.predicted_stabilization_time_after
  if (before == null || after == null) return 'Not enough transition history'
  return stabilizationGain(item) > 0
    ? `${formatNumber(stabilizationGain(item), 0)} steps`
    : 'No measurable improvement'
}

function visibleInferenceSources(item: ForecastRecommendation, correlationVariables: Set<string>) {
  return item.inference_sources.filter((source) => {
    if (source === 'Forecast') return true
    if (source === 'Recipe Constraint') return item.constraint_validation.recipe_rules.length > 0
    if (source === 'Historical Successful Transition') {
      return item.historical_evidence.historical_effectiveness > 0
    }
    if (source === 'Historical Trend') return item.historical_evidence.similar_transition_count > 0
    if (source === 'Correlation Analysis') {
      return item.affected_variables.some((variable) => correlationVariables.has(variable))
    }
    return false
  })
}

function formatTime(timestamp: string) {
  return new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit' }).format(
    new Date(timestamp),
  )
}

function RecommendationSkeletons() {
  return (
    <div className="grid animate-pulse gap-3 md:grid-cols-2 xl:grid-cols-3" role="status">
      {['Running sequential prediction…', 'Finding similar transitions…', 'Validating recipe constraints…'].map(
        (label) => (
          <div key={label} className="rounded-xl bg-slate-100 p-4 dark:bg-white/[0.04]">
            <div className="h-3 w-2/3 rounded bg-slate-200 dark:bg-white/10" />
            <p className="mt-3 text-xs text-slate-500">{label}</p>
          </div>
        ),
      )}
    </div>
  )
}

function formatSteps(value: number | null) {
  return value == null ? '—' : `${formatNumber(value, 0)} steps`
}
