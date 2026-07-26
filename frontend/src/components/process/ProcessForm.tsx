import type { FormEvent } from 'react'

import type { ProcessInput } from '../../api/types'
import { grades, numericFields } from '../../config/process'

export function ProcessForm({
  values,
  onChange,
  onSubmit,
  submitLabel,
  busy = false,
  compact = false,
}: {
  values: ProcessInput
  onChange: (values: ProcessInput) => void
  onSubmit: (event: FormEvent) => void
  submitLabel: string
  busy?: boolean
  compact?: boolean
}) {
  const inputClass =
    'mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-cyan-500 focus:ring-2 focus:ring-cyan-400/20 dark:border-white/10 dark:bg-white/[0.04] dark:text-white'
  return (
    <form onSubmit={onSubmit}>
      <div className={`grid gap-4 ${compact ? 'sm:grid-cols-2' : 'sm:grid-cols-2 xl:grid-cols-3'}`}>
        {(['current_grade', 'target_grade'] as const).map((key) => (
          <label key={key} className="text-sm font-medium text-slate-700 dark:text-slate-300">
            {key === 'current_grade' ? 'Current Grade' : 'Target Grade'}
            <select
              className={inputClass}
              value={values[key]}
              onChange={(event) => onChange({ ...values, [key]: event.target.value })}
            >
              {grades.map((grade) => (
                <option key={grade}>{grade}</option>
              ))}
            </select>
          </label>
        ))}
        {numericFields.map((field) => (
          <label
            key={field.key}
            htmlFor={field.key}
            className="text-sm font-medium text-slate-700 dark:text-slate-300"
          >
            <span className="flex justify-between">
              {field.label}
              <span className="font-normal text-slate-500">{field.unit}</span>
            </span>
            <input
              id={field.key}
              required
              type="number"
              className={inputClass}
              min={field.min}
              max={field.max}
              step={field.step}
              value={values[field.key]}
              onChange={(event) => onChange({ ...values, [field.key]: Number(event.target.value) })}
              aria-describedby={`${field.key}-range`}
            />
            <span id={`${field.key}-range`} className="sr-only">
              Valid range {field.min} to {field.max} {field.unit}
            </span>
          </label>
        ))}
      </div>
      <button
        disabled={busy}
        className="mt-6 rounded-xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-ink-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {busy ? 'Processing…' : submitLabel}
      </button>
    </form>
  )
}
