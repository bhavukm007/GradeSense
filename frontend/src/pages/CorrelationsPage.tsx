import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { api } from '../api/client'
import { PageHeader } from '../components/ui/PageHeader'
import { Panel } from '../components/ui/Panel'
import { ErrorState, SkeletonGrid } from '../components/ui/QueryState'
import { useRelationshipDiscoveries } from '../hooks/useRelationshipDiscoveries'
import { formatNumber, labelize } from '../lib/format'

export function CorrelationsPage() {
  const [search, setSearch] = useState('')
  const [threshold, setThreshold] = useState(0.3)
  const query = useQuery({
    queryKey: ['correlations'],
    queryFn: () => api.correlations(50),
    staleTime: 300_000,
  })
  const discoveryQueries = useRelationshipDiscoveries(10)
  const discoveries = discoveryQueries
    .flatMap((item) => item.data?.relationships ?? [])
    .sort((first, second) => second.strength - first.strength)
    .slice(0, 10)
  const variables = useMemo(
    () =>
      query.data
        ? Object.keys(query.data.correlation_matrix).filter((name) =>
            name.includes(search.toLowerCase().replaceAll(' ', '_')),
          )
        : [],
    [query.data, search],
  )
  return (
    <>
      <PageHeader
        eyebrow="Relationship discovery"
        title="Correlation explorer"
        description="Search and filter the dataset correlation matrix to locate strong positive and negative process relationships."
      />
      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <input
          className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm dark:border-white/10 dark:bg-white/[0.04]"
          placeholder="Search variables…"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <label className="flex items-center gap-3 rounded-xl border border-slate-300 px-4 py-2 text-sm dark:border-white/10">
          Minimum strength{' '}
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={threshold}
            onChange={(event) => setThreshold(Number(event.target.value))}
          />
          <b>{threshold.toFixed(2)}</b>
        </label>
      </div>
      {query.isLoading ? (
        <div className="mt-5">
          <SkeletonGrid count={2} />
        </div>
      ) : query.error ? (
        <div className="mt-5">
          <ErrorState message={query.error.message} />
        </div>
      ) : (
        <>
          <Panel className="mt-5" title="Top 10 discovered transition relationships">
            <p className="mb-4 text-sm text-slate-500">
              Lag, nonlinear, and interaction analysis against Basis Weight deviation, separated by
              transition stage.
            </p>
            <div className="grid gap-3 lg:grid-cols-2">
              {discoveries.map((item, index) => (
                <div
                  key={`${item.stage}-${item.relationship_type}-${item.variable}-${item.interacts_with ?? index}`}
                  className="rounded-xl border border-slate-200 p-4 dark:border-white/10"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-semibold">
                      {labelize(item.variable)}
                      {item.interacts_with
                        ? ` × ${labelize(item.interacts_with)}`
                        : ' → Basis Weight'}
                    </p>
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                        item.severity === 'High'
                          ? 'bg-rose-400/10 text-rose-500'
                          : item.severity === 'Medium'
                            ? 'bg-amber-400/10 text-amber-500'
                            : 'bg-emerald-400/10 text-emerald-500'
                      }`}
                    >
                      {item.severity} impact
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-slate-500">{item.summary}</p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    <span className="rounded-full bg-cyan-400/10 px-2 py-1 text-cyan-500">
                      {item.relationship_type}
                    </span>
                    <span className="rounded-full bg-indigo-400/10 px-2 py-1 text-indigo-500">
                      {item.stage}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2 py-1 dark:bg-white/10">
                      Strength {formatNumber(item.strength, 3)}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2 py-1 dark:bg-white/10">
                      {item.impact_direction}
                    </span>
                    {item.best_lag != null && (
                      <span className="rounded-full bg-slate-100 px-2 py-1 dark:bg-white/10">
                        Best lag {item.best_lag}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Panel>
          <Panel className="mt-5 overflow-hidden" title="Interactive correlation heatmap">
            <div className="max-h-[650px] overflow-auto">
              <div
                className="grid min-w-max"
                style={{ gridTemplateColumns: `140px repeat(${variables.length}, 42px)` }}
              >
                <div />
                {variables.map((name) => (
                  <div
                    key={name}
                    className="h-36 [writing-mode:vertical-rl] rotate-180 truncate px-2 text-xs text-slate-500"
                  >
                    {labelize(name)}
                  </div>
                ))}
                {variables.flatMap((row) => [
                  <div key={`${row}-label`} className="truncate pr-3 text-xs leading-[42px]">
                    {labelize(row)}
                  </div>,
                  ...variables.map((column) => {
                    const value = query.data!.correlation_matrix[column][row]
                    const visible = Math.abs(value) >= threshold || row === column
                    const color =
                      value >= 0
                        ? `rgba(45,212,191,${visible ? Math.abs(value) : 0.03})`
                        : `rgba(244,63,94,${visible ? Math.abs(value) : 0.03})`
                    return (
                      <div
                        title={`${labelize(row)} / ${labelize(column)}: ${value}`}
                        key={`${row}-${column}`}
                        className="grid size-[42px] place-items-center border border-white/5 text-[9px]"
                        style={{ backgroundColor: color }}
                      >
                        {visible ? value.toFixed(1) : ''}
                      </div>
                    )
                  }),
                ])}
              </div>
            </div>
          </Panel>
          <div className="mt-5 grid gap-5 lg:grid-cols-2">
            {(
              [
                [
                  'Strongest positive',
                  query.data!.strongest_positive_correlations,
                  'text-emerald-500',
                ],
                [
                  'Strongest negative',
                  query.data!.strongest_negative_correlations,
                  'text-rose-500',
                ],
              ] as const
            ).map(([title, pairs, tone]) => (
              <Panel key={title} title={title}>
                <div className="space-y-3">
                  {pairs
                    .filter(
                      (pair) =>
                        Math.abs(pair.correlation) >= threshold &&
                        (`${pair.first_variable} ${pair.second_variable}`.includes(
                          search.toLowerCase().replaceAll(' ', '_'),
                        ) ||
                          !search),
                    )
                    .map((pair) => (
                      <div
                        key={`${pair.first_variable}-${pair.second_variable}`}
                        className="flex justify-between gap-3 rounded-xl bg-slate-50 p-3 text-sm dark:bg-white/[0.04]"
                      >
                        <span>
                          {labelize(pair.first_variable)} ↔ {labelize(pair.second_variable)}
                        </span>
                        <b className={tone}>{formatNumber(pair.correlation, 3)}</b>
                      </div>
                    ))}
                </div>
              </Panel>
            ))}
          </div>
        </>
      )}
    </>
  )
}
