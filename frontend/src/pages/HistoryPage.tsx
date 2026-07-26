import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { api } from '../api/client'
import type { PredictionHistoryItem } from '../api/types'
import { Pagination } from '../components/history/Pagination'
import { PageHeader } from '../components/ui/PageHeader'
import { Panel } from '../components/ui/Panel'
import { EmptyMessage, ErrorState, SkeletonGrid } from '../components/ui/QueryState'
import { formatDate, formatNumber, formatPercent } from '../lib/format'

export function HistoryPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<'newest' | 'quality' | 'risk'>('newest')
  const [selected, setSelected] = useState<PredictionHistoryItem>()
  const query = useQuery({
    queryKey: ['prediction-history', page, 20],
    queryFn: () => api.predictionHistory(page, 20),
  })
  const rows = useMemo(() => {
    const filtered = (query.data?.items ?? []).filter((row) =>
      `${row.input_data.current_grade} ${row.input_data.target_grade} ${row.prediction_id}`
        .toLowerCase()
        .includes(search.toLowerCase()),
    )
    return [...filtered].sort((a, b) =>
      sort === 'quality'
        ? b.quality_score - a.quality_score
        : sort === 'risk'
          ? b.off_spec_probability - a.off_spec_probability
          : Date.parse(b.created_at) - Date.parse(a.created_at),
    )
  }, [query.data, search, sort])
  return (
    <>
      <PageHeader
        eyebrow="Operational record"
        title="Prediction history"
        description="Search, sort, inspect, and paginate every persisted transition prediction."
      />
      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <input
          className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm dark:border-white/10 dark:bg-white/[0.04]"
          placeholder="Search grade or prediction ID…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm dark:border-white/10 dark:bg-ink-900"
          value={sort}
          onChange={(e) => setSort(e.target.value as typeof sort)}
        >
          <option value="newest">Newest first</option>
          <option value="quality">Highest quality</option>
          <option value="risk">Highest risk</option>
        </select>
      </div>
      {query.isLoading ? (
        <div className="mt-5">
          <SkeletonGrid />
        </div>
      ) : query.error ? (
        <div className="mt-5">
          <ErrorState message={query.error.message} />
        </div>
      ) : (
        <Panel className="mt-5 overflow-hidden">
          {rows.length ? (
            <div className="overflow-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="text-xs uppercase text-slate-500">
                  <tr>
                    <th className="py-3">Timestamp</th>
                    <th>Transition</th>
                    <th>Quality</th>
                    <th>Off-spec</th>
                    <th>Stabilization</th>
                    <th />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-white/[0.06]">
                  {rows.map((row) => (
                    <tr key={row.prediction_id}>
                      <td className="py-4">{formatDate(row.created_at)}</td>
                      <td>
                        {row.input_data.current_grade} → {row.input_data.target_grade}
                      </td>
                      <td>{formatNumber(row.quality_score)}</td>
                      <td>{formatPercent(row.off_spec_probability)}</td>
                      <td>{formatNumber(row.expected_stabilization_time)} min</td>
                      <td>
                        <button
                          className="font-semibold text-cyan-500"
                          onClick={() => setSelected(row)}
                        >
                          Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyMessage>No predictions match the current search.</EmptyMessage>
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
          aria-label="Prediction details"
        >
          <Panel
            className="max-h-[85vh] w-full max-w-2xl overflow-auto"
            title="Prediction details"
            action={<button onClick={() => setSelected(undefined)}>Close</button>}
          >
            <p className="text-sm leading-6">{selected.explanation.summary}</p>
            <pre className="mt-4 overflow-auto rounded-xl bg-slate-950 p-4 text-xs text-slate-300">
              {JSON.stringify(selected.input_data, null, 2)}
            </pre>
            <p className="mt-4 break-all text-xs text-slate-500">{selected.prediction_id}</p>
          </Panel>
        </div>
      )}
    </>
  )
}
