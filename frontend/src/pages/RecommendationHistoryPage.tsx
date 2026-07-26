import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { api } from '../api/client'
import type {
  ForecastRecommendation,
  RecommendationHistoryItem,
  RecommendationOutcome,
  TrajectoryPoint,
} from '../api/types'
import { Pagination } from '../components/history/Pagination'
import { PageHeader } from '../components/ui/PageHeader'
import { Panel } from '../components/ui/Panel'
import { EmptyMessage, ErrorState, SkeletonGrid } from '../components/ui/QueryState'
import { formatDate, formatPercent } from '../lib/format'

export function RecommendationHistoryPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<RecommendationHistoryItem>()
  const [outcomeRecommendation, setOutcomeRecommendation] = useState<ForecastRecommendation>()
  const query = useQuery({
    queryKey: ['recommendation-history', page, 20],
    queryFn: () => api.recommendationHistory(page, 20),
  })
  const interventionQuery = useQuery({
    queryKey: ['intervention-history'],
    queryFn: api.interventionHistory,
  })
  const effectiveness = useQuery({
    queryKey: ['intervention-effectiveness'],
    queryFn: api.interventionEffectiveness,
  })
  const rows = useMemo(
    () =>
      (query.data?.items ?? []).filter((row) =>
        `${row.recommendation_id} ${row.recommendations.map((item) => item.text).join(' ')}`
          .toLowerCase()
          .includes(search.toLowerCase()),
      ),
    [query.data, search],
  )
  return (
    <>
      <PageHeader
        eyebrow="Decision audit"
        title="Recommendation history"
        description="Review every persisted model-evaluated intervention and its supporting confidence."
      />
      <input
        className="mt-8 w-full max-w-md rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm dark:border-white/10 dark:bg-white/[0.04]"
        placeholder="Search recommendation text or ID…"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />
      <div className="mt-5 grid gap-4 sm:grid-cols-3">
        <Panel title="Evaluated outcomes">
          <p className="text-2xl font-semibold">{effectiveness.data?.evaluated_count ?? 0}</p>
        </Panel>
        <Panel title="Crossing avoidance">
          <p className="text-2xl font-semibold">
            {formatPercent(effectiveness.data?.crossing_avoidance_rate ?? 0)}
          </p>
        </Panel>
        <Panel title="Mean deviation improvement">
          <p className="text-2xl font-semibold">
            {(effectiveness.data?.mean_deviation_improvement ?? 0).toFixed(2)}%
          </p>
        </Panel>
      </div>
      {!!interventionQuery.data?.length && (
        <Panel className="mt-5" title="Forecast intervention lifecycle">
          <div className="space-y-2">
            {interventionQuery.data.map((item) => (
              <button
                type="button"
                key={item.recommendation_id}
                onClick={() => setOutcomeRecommendation(item)}
                className="flex w-full items-center justify-between rounded-xl bg-slate-50 p-3 text-left text-sm transition hover:bg-slate-100 dark:bg-white/[0.04] dark:hover:bg-white/[0.08]"
              >
                <span>
                  #{item.rank} {item.affected_variables.join(', ')}
                </span>
                <span className="flex items-center gap-3">
                  <span className="font-semibold uppercase text-cyan-500">{item.state}</span>
                  <span className="text-xs font-semibold text-slate-500">
                    {item.state === 'accepted' || item.state === 'applied'
                      ? 'Evaluate outcome'
                      : 'Review'}
                  </span>
                </span>
              </button>
            ))}
          </div>
        </Panel>
      )}
      {query.isLoading ? (
        <div className="mt-5">
          <SkeletonGrid />
        </div>
      ) : query.error ? (
        <div className="mt-5">
          <ErrorState message={query.error.message} />
        </div>
      ) : (
        <Panel className="mt-5">
          {rows.length ? (
            <div className="space-y-3">
              {rows.map((row) => (
                <button
                  key={row.recommendation_id}
                  onClick={() => setSelected(row)}
                  className="flex w-full items-center justify-between gap-4 rounded-xl bg-slate-50 p-4 text-left dark:bg-white/[0.04]"
                >
                  <div>
                    <p className="font-medium">
                      {row.recommendations[0]?.text ?? 'No action required'}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      {formatDate(row.created_at)} · {row.recommendations.length} action(s)
                    </p>
                  </div>
                  <span className="text-sm font-semibold text-cyan-500">Details</span>
                </button>
              ))}
            </div>
          ) : (
            <EmptyMessage>No recommendations match the current search.</EmptyMessage>
          )}
          <Pagination
            page={page}
            totalPages={query.data!.pagination.total_pages}
            onChange={setPage}
          />
        </Panel>
      )}
      {selected && (
        <div
          className="fixed inset-0 z-[70] grid place-items-center bg-slate-950/70 p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Recommendation details"
        >
          <Panel
            className="w-full max-w-2xl"
            title="Recommendation details"
            action={<button onClick={() => setSelected(undefined)}>Close</button>}
          >
            <div className="space-y-3">
              {selected.recommendations.map((item) => (
                <div key={item.text} className="rounded-xl bg-slate-50 p-4 dark:bg-white/[0.04]">
                  <p className="font-medium">{item.text}</p>
                  <p className="mt-2 text-sm text-slate-500">
                    {formatPercent(item.confidence)} confidence · {item.expected_improvement}{' '}
                    expected improvement
                  </p>
                </div>
              ))}
            </div>
            <p className="mt-4 break-all text-xs text-slate-500">{selected.recommendation_id}</p>
          </Panel>
        </div>
      )}
      {outcomeRecommendation && (
        <OutcomeEvaluationDialog
          recommendation={outcomeRecommendation}
          onClose={() => setOutcomeRecommendation(undefined)}
        />
      )}
    </>
  )
}

function OutcomeEvaluationDialog({
  recommendation,
  onClose,
}: {
  recommendation: ForecastRecommendation
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [observations, setObservations] = useState<TrajectoryPoint[]>(
    recommendation.intervention_trajectory.map((point) => ({ ...point })),
  )
  const [notes, setNotes] = useState('')
  const [result, setResult] = useState<RecommendationOutcome>()
  const eligible = recommendation.state === 'accepted' || recommendation.state === 'applied'
  const evaluation = useMutation({
    mutationFn: async () => {
      await api.decideRecommendation(recommendation.recommendation_id, {
        operator_action: 'applied',
        reason: 'Outcome observations submitted',
        notes: notes.trim() || undefined,
      })
      return api.evaluateRecommendationOutcome(recommendation.recommendation_id, { observations })
    },
    onSuccess: (outcome) => {
      setResult(outcome)
      void queryClient.invalidateQueries({ queryKey: ['intervention-history'] })
      void queryClient.invalidateQueries({ queryKey: ['intervention-effectiveness'] })
    },
  })

  const updateBasisWeight = (index: number, basisWeight: number) => {
    setObservations((current) =>
      current.map((point, pointIndex) =>
        pointIndex === index
          ? {
              ...point,
              basis_weight: basisWeight,
              deviation_pct:
                ((basisWeight - (point.lower_spec_limit + point.upper_spec_limit) / 2) /
                  ((point.lower_spec_limit + point.upper_spec_limit) / 2)) *
                100,
            }
          : point,
      ),
    )
  }

  return (
    <div
      className="fixed inset-0 z-[80] grid place-items-center overflow-y-auto bg-slate-950/70 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Evaluate recommendation outcome"
    >
      <Panel
        className="my-6 w-full max-w-4xl"
        title={result ? 'Outcome evaluation complete' : 'Submit observed outcome'}
        action={<button onClick={onClose}>Close</button>}
      >
        <div className="grid gap-3 text-sm sm:grid-cols-3">
          <OutcomeStat label="Recommendation state" value={recommendation.state.toUpperCase()} />
          <OutcomeStat label="Created" value={formatDate(recommendation.created_at)} />
          <OutcomeStat label="Last updated" value={formatDate(recommendation.updated_at)} />
        </div>

        {!eligible && !result ? (
          <div className="mt-5 rounded-xl bg-amber-400/10 p-4 text-sm text-amber-600">
            Outcome evaluation is available only after a recommendation has been accepted or
            applied. This recommendation is currently {recommendation.state}.
          </div>
        ) : result ? (
          <>
            <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <OutcomeStat
                label="Predicted peak before"
                value={`${recommendation.metrics.predicted_peak_deviation_before.toFixed(2)}%`}
              />
              <OutcomeStat
                label="Predicted peak after"
                value={`${recommendation.metrics.predicted_peak_deviation_after.toFixed(2)}%`}
              />
              <OutcomeStat
                label="Actual vs predicted"
                value={`${result.metrics.actual_vs_predicted_deviation.toFixed(2)}%`}
              />
              <OutcomeStat
                label="Prediction accuracy"
                value={formatPercent(result.metrics.prediction_accuracy)}
              />
            </div>
            <div className="mt-4 rounded-xl bg-emerald-400/10 p-4 text-sm">
              <p className="font-semibold text-emerald-600">
                Evaluated {formatDate(result.evaluated_at)}
              </p>
              <p className="mt-2 text-slate-600 dark:text-slate-300">
                Crossing avoided: {result.metrics.crossing_avoided ? 'Yes' : 'No'} · Deviation
                improvement: {result.metrics.deviation_improvement.toFixed(2)}% · Stabilization
                improvement: {result.metrics.stabilization_improvement.toFixed(0)} steps
              </p>
              <p className="mt-3 text-slate-500">
                Operator notes: {notes.trim() || 'No notes provided.'}
              </p>
            </div>
          </>
        ) : (
          <form
            className="mt-5"
            onSubmit={(event) => {
              event.preventDefault()
              evaluation.mutate()
            }}
          >
            <p className="text-sm text-slate-500">
              Replace the predicted Basis Weight values with the actual observations recorded at
              each forecast timestamp. Submitting also records the recommendation as applied.
            </p>
            <div className="mt-4 max-h-80 overflow-auto rounded-xl border border-slate-200 dark:border-white/10">
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 bg-slate-100 dark:bg-ink-900">
                  <tr>
                    <th className="p-3">Timestamp</th>
                    <th className="p-3">Predicted</th>
                    <th className="p-3">Actual Basis Weight</th>
                  </tr>
                </thead>
                <tbody>
                  {observations.map((point, index) => (
                    <tr
                      key={`${point.timestamp}-${point.step}`}
                      className="border-t border-slate-200 dark:border-white/10"
                    >
                      <td className="p-3 text-xs text-slate-500">{formatDate(point.timestamp)}</td>
                      <td className="p-3">
                        {recommendation.intervention_trajectory[index].basis_weight.toFixed(2)}
                      </td>
                      <td className="p-3">
                        <input
                          aria-label={`Actual Basis Weight at step ${point.step}`}
                          required
                          type="number"
                          step="0.01"
                          value={point.basis_weight}
                          onChange={(event) => updateBasisWeight(index, Number(event.target.value))}
                          className="w-36 rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-white/10 dark:bg-white/[0.04]"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <label className="mt-4 block text-sm font-medium">
              Operator notes
              <textarea
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="Describe the applied change and observed process response"
                className="mt-2 min-h-24 w-full rounded-xl border border-slate-300 bg-white p-3 dark:border-white/10 dark:bg-white/[0.04]"
              />
            </label>
            {evaluation.error && (
              <div className="mt-4">
                <ErrorState message={evaluation.error.message} />
              </div>
            )}
            <button
              disabled={evaluation.isPending}
              className="mt-4 rounded-xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-ink-950 disabled:opacity-60"
            >
              {evaluation.isPending ? 'Evaluating…' : 'Submit observed outcome'}
            </button>
          </form>
        )}
      </Panel>
    </div>
  )
}

function OutcomeStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3 dark:bg-white/[0.04]">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 font-semibold">{value}</p>
    </div>
  )
}
