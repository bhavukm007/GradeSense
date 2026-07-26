import { AlertTriangle, RefreshCw } from 'lucide-react'
import type { PropsWithChildren } from 'react'

export function SkeletonGrid({ count = 4 }: { count?: number }) {
  return (
    <div className="grid animate-pulse gap-4 sm:grid-cols-2 xl:grid-cols-4" role="status">
      {Array.from({ length: count }, (_, index) => (
        <div
          key={index}
          className="h-32 rounded-2xl border border-slate-200 bg-slate-200/60 dark:border-white/[0.06] dark:bg-white/[0.05]"
        />
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
              className="mt-4 inline-flex items-center gap-2 text-sm font-semibold"
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
    <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-white/10">
      {children}
    </div>
  )
}
