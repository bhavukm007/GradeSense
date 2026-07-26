import type { LucideIcon } from 'lucide-react'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description: string
}

export function EmptyState({ icon: Icon, title, description }: EmptyStateProps) {
  return (
    <section className="mt-8 overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-panel dark:border-white/[0.08] dark:bg-ink-900">
      <div className="relative grid min-h-[430px] place-items-center px-6 py-16 text-center">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_20%,rgba(45,212,191,0.08),transparent_45%)]" />
        <div className="relative max-w-md">
          <div className="mx-auto grid size-16 place-items-center rounded-2xl border border-cyan-500/20 bg-cyan-500/10 text-cyan-500 dark:text-cyan-400">
            <Icon className="size-7" />
          </div>
          <h2 className="mt-6 text-xl font-semibold tracking-tight text-slate-900 dark:text-white">
            {title}
          </h2>
          <p className="mt-3 text-sm leading-6 text-slate-500 dark:text-slate-400">{description}</p>
          <div className="mx-auto mt-7 inline-flex items-center gap-2 rounded-full border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-500 dark:border-white/10 dark:text-slate-400">
            <span className="size-1.5 rounded-full bg-amber-400" />
            Planned for a future phase
          </div>
        </div>
      </div>
    </section>
  )
}
