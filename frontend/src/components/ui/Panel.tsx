import type { PropsWithChildren, ReactNode } from 'react'

export function Panel({
  children,
  className = '',
  title,
  action,
  id,
}: PropsWithChildren<{ className?: string; title?: string; action?: ReactNode; id?: string }>) {
  return (
    <section
      id={id}
      className={`min-w-0 rounded-2xl border border-slate-200/90 bg-white p-4 shadow-panel sm:p-5 dark:border-white/[0.08] dark:bg-ink-900 ${className}`}
    >
      {(title || action) && (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          {title && (
            <h2 className="text-base font-semibold tracking-tight text-slate-950 dark:text-white">
              {title}
            </h2>
          )}
          {action}
        </div>
      )}
      {children}
    </section>
  )
}
