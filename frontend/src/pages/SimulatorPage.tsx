import { useMutation } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, Minus } from 'lucide-react'
import { useState } from 'react'

import { api } from '../api/client'
import type { Prediction, ProcessInput } from '../api/types'
import { defaultProcessInput } from '../config/process'
import { ProcessForm } from '../components/process/ProcessForm'
import { PageHeader } from '../components/ui/PageHeader'
import { Panel } from '../components/ui/Panel'
import { ErrorState } from '../components/ui/QueryState'
import { formatNumber } from '../lib/format'
import { useProcessStore } from '../stores/processStore'
import { InterventionForecast } from '../components/forecast/InterventionForecast'

function Delta({
  value,
  inverse = false,
  suffix = '',
}: {
  value: number
  inverse?: boolean
  suffix?: string
}) {
  const improved = inverse ? value < 0 : value > 0
  const Icon = value === 0 ? Minus : value > 0 ? ArrowUp : ArrowDown
  return (
    <span
      className={`inline-flex items-center gap-1 text-sm font-semibold ${value === 0 ? 'text-slate-500' : improved ? 'text-emerald-500' : 'text-rose-500'}`}
    >
      <Icon className="size-4" />
      {formatNumber(Math.abs(value), 2)}
      {suffix}
    </span>
  )
}

export function SimulatorPage() {
  const stored = useProcessStore((state) => state.baseline)
  const [values, setValues] = useState<ProcessInput>(stored ?? defaultProcessInput)
  const [baseline, setBaseline] = useState<Prediction>()
  const mutation = useMutation({
    mutationFn: async (input: ProcessInput) => {
      const original = baseline ?? (await api.predict(stored ?? defaultProcessInput))
      const candidate = await api.predict(input)
      return { original, candidate }
    },
    onSuccess: ({ original }) => setBaseline(original),
  })
  const result = mutation.data
  return (
    <>
      <PageHeader
        eyebrow="Safe experimentation"
        title="What-if simulator"
        description="Compare an adjusted process scenario with the last prediction baseline. This uses inference only—the model is never retrained."
      />
      <Panel className="mt-8" title="Candidate process conditions">
        <ProcessForm
          compact
          values={values}
          onChange={setValues}
          busy={mutation.isPending}
          submitLabel="Compare scenario"
          onSubmit={(event) => {
            event.preventDefault()
            mutation.mutate(values)
          }}
        />
      </Panel>
      {mutation.error && (
        <div className="mt-5">
          <ErrorState message={mutation.error.message} />
        </div>
      )}
      {result && (
        <div className="mt-5 grid gap-4 md:grid-cols-3" aria-live="polite">
          {[
            [
              'Quality score',
              result.original.quality_score,
              result.candidate.quality_score,
              false,
              '',
            ],
            [
              'Off-spec risk',
              result.original.off_spec_probability * 100,
              result.candidate.off_spec_probability * 100,
              true,
              '%',
            ],
            [
              'Stabilization',
              result.original.expected_stabilization_time,
              result.candidate.expected_stabilization_time,
              true,
              ' min',
            ],
          ].map(([label, before, after, inverse, suffix]) => (
            <Panel key={String(label)}>
              <p className="text-sm font-semibold">{label}</p>
              <div className="mt-4 flex items-end justify-between gap-3">
                <div>
                  <p className="text-xs text-slate-500">Before</p>
                  <p className="text-xl font-semibold">
                    {formatNumber(Number(before))}
                    {suffix}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-slate-500">After</p>
                  <p className="text-xl font-semibold">
                    {formatNumber(Number(after))}
                    {suffix}
                  </p>
                </div>
              </div>
              <div className="mt-4 border-t border-slate-200 pt-3 dark:border-white/10">
                <Delta
                  value={Number(after) - Number(before)}
                  inverse={Boolean(inverse)}
                  suffix={String(suffix)}
                />
              </div>
            </Panel>
          ))}
        </div>
      )}
      <InterventionForecast />
    </>
  )
}
