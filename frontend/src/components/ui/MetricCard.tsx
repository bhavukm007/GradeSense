import type { LucideIcon } from 'lucide-react'

export function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  tone = 'cyan',
}: {
  label: string
  value: string
  detail?: string
  icon: LucideIcon
  tone?: 'cyan' | 'emerald' | 'amber' | 'rose'
}) {
  const tones = {
    cyan: 'bg-cyan-400/10 text-cyan-500',
    emerald: 'bg-emerald-400/10 text-emerald-500',
    amber: 'bg-amber-400/10 text-amber-500',
    rose: 'bg-rose-400/10 text-rose-500',
  }
  return (
    <div className="flex min-h-40 min-w-0 flex-col rounded-2xl border border-slate-200/90 bg-white p-5 shadow-panel dark:border-white/[0.08] dark:bg-ink-900">
      <div className={`grid size-10 place-items-center rounded-xl ${tones[tone]}`}>
        <Icon className="size-5" />
      </div>
      <p className="mt-4 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
        {label}
      </p>
      <p className="mt-1 break-words text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">
        {value}
      </p>
      {detail && <p className="mt-auto break-words pt-2 text-xs leading-5 text-slate-500">{detail}</p>}
    </div>
  )
}
