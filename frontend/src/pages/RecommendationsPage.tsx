import { useMutation, useQueryClient } from '@tanstack/react-query'
import { CircleCheck, Lightbulb } from 'lucide-react'

import { api } from '../api/client'
import type { Recommendation } from '../api/types'
import { ProcessForm } from '../components/process/ProcessForm'
import { PageHeader } from '../components/ui/PageHeader'
import { Panel } from '../components/ui/Panel'
import { EmptyMessage, ErrorState } from '../components/ui/QueryState'
import { formatNumber, formatPercent, labelize } from '../lib/format'
import { useProcessStore } from '../stores/processStore'

function priority(item: Recommendation) {
  if (item.confidence >= 0.8 || item.expected_improvement >= 5) return 'High'
  if (item.confidence >= 0.65 || item.expected_improvement >= 2) return 'Medium'
  return 'Low'
}

export function RecommendationsPage() {
  const { values, setValues } = useProcessStore()
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: api.recommend,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['recommendation-history'] })
      void queryClient.invalidateQueries({ queryKey: ['prediction-history'] })
    },
  })
  return (
    <>
      <PageHeader
        eyebrow="Decision support"
        title="Recommendation center"
        description="Evaluate targeted process interventions against the active model before changing operating conditions."
      />
      <Panel className="mt-8" title="Transition conditions">
        <ProcessForm
          compact
          values={values}
          onChange={setValues}
          busy={mutation.isPending}
          submitLabel="Generate recommendations"
          onSubmit={(event) => {
            event.preventDefault()
            mutation.mutate(values)
          }}
        />
      </Panel>
      {mutation.error && (
        <div className="mt-5">
          <ErrorState message={mutation.error.message} onRetry={() => mutation.mutate(values)} />
        </div>
      )}
      {mutation.data && (
        <div className="mt-5 space-y-4" aria-live="polite">
          {mutation.data.recommendations.length === 0 ? (
            <EmptyMessage>
              <CircleCheck className="mx-auto mb-3 size-7 text-emerald-500" />
              No action required. The model found no evaluated intervention that improves this
              transition.
            </EmptyMessage>
          ) : (
            mutation.data.recommendations.map((item, index) => (
              <Panel key={`${item.text}-${index}`}>
                <div className="flex flex-col gap-4 sm:flex-row">
                  <div className="grid size-11 shrink-0 place-items-center rounded-xl bg-amber-400/10 text-amber-500">
                    <Lightbulb className="size-5" />
                  </div>
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-semibold">{item.text}</h2>
                      <span className="rounded-full bg-cyan-400/10 px-2.5 py-1 text-xs font-semibold text-cyan-500">
                        {priority(item)} priority
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-slate-500">
                      This candidate was retained because its model-evaluated quality, risk, and
                      stabilization objective improves on the submitted baseline.
                    </p>
                    <div className="mt-4 flex flex-wrap gap-4 text-sm">
                      <span>
                        <b>{formatPercent(item.confidence)}</b> confidence
                      </span>
                      <span>
                        <b>{formatNumber(item.expected_improvement, 2)}</b> expected improvement
                      </span>
                      <span>
                        Affects <b>{item.affected_variables.map(labelize).join(', ')}</b>
                      </span>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {item.inference_sources.map((source) => (
                        <span
                          key={source}
                          className="rounded-full bg-indigo-400/10 px-2.5 py-1 text-xs font-semibold text-indigo-500"
                        >
                          {source}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </Panel>
            ))
          )}
          <p className="text-xs text-slate-500">
            Recommendation ID: {mutation.data.recommendation_id}
          </p>
        </div>
      )}
    </>
  )
}
