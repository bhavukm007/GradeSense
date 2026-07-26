import { AlertTriangle, RefreshCw } from 'lucide-react'
import type { PropsWithChildren } from 'react'

export function SkeletonGrid({ count = 4 }: { count?: number }) {
  return (
    <div className="grid animate-pulse gap-4 sm:grid-cols-2 xl:grid-cols-4" role="status">
      {Array.from({ length: count }, (_, index) => (
        <div
          key={index}
          className="h-36 overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 dark:border-white/[0.06] dark:bg-white/[0.05]"
        >
          <div className="size-10 rounded-xl bg-slate-200 dark:bg-white/10" />
          <div className="mt-5 h-3 w-2/5 rounded bg-slate-200 dark:bg-white/10" />
          <div className="mt-3 h-6 w-3/5 rounded bg-slate-200 dark:bg-white/10" />
        </div>
      ))}
      <span className="sr-only">Loading</span>
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-2xl border border-rose-300/50 bg-rose-50 p-6 text-rose-800 dark:border-rose-400/20 dark:bg-rose-400/10 dark:text-rose-200">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 size-5 shrink-0" />
        <div>
          <p className="font-semibold">Data unavailable</p>
          <p className="mt-1 text-sm opacity-80">{message}</p>
          {onRetry && (
            <button
              className="mt-4 inline-flex items-center gap-2 rounded-lg px-2 text-sm font-semibold hover:bg-rose-500/10"
              onClick={onRetry}
            >
              <RefreshCw className="size-4" /> Retry
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export function EmptyMessage({ children }: PropsWithChildren) {
  return (
    <div className="grid min-h-36 place-items-center rounded-xl border border-dashed border-slate-300 bg-slate-50/50 p-6 text-center text-sm leading-6 text-slate-500 dark:border-white/10 dark:bg-white/[0.02]">
      {children}
    </div>
  )
}
