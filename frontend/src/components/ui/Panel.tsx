import type { PropsWithChildren, ReactNode } from 'react'

export function Panel({
  children,
  className = '',
  title,
  action,
}: PropsWithChildren<{ className?: string; title?: string; action?: ReactNode }>) {
  return (
    <section
      className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-panel dark:border-white/[0.08] dark:bg-ink-900 ${className}`}
    >
      {(title || action) && (
        <div className="mb-5 flex items-center justify-between gap-4">
          {title && <h2 className="font-semibold text-slate-950 dark:text-white">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  )
}
