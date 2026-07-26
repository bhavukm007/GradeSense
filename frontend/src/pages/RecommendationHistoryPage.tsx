import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { api } from '../api/client'
import type { RecommendationHistoryItem } from '../api/types'
import { Pagination } from '../components/history/Pagination'
import { PageHeader } from '../components/ui/PageHeader'
import { Panel } from '../components/ui/Panel'
import { EmptyMessage, ErrorState, SkeletonGrid } from '../components/ui/QueryState'
import { formatDate, formatPercent } from '../lib/format'

export function RecommendationHistoryPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<RecommendationHistoryItem>()
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
              <div
                key={item.recommendation_id}
                className="flex justify-between rounded-xl bg-slate-50 p-3 text-sm dark:bg-white/[0.04]"
              >
                <span>
                  #{item.rank} {item.affected_variables.join(', ')}
                </span>
                <span className="font-semibold uppercase text-cyan-500">{item.state}</span>
              </div>
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
    </>
  )
}
