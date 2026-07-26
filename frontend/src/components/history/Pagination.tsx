export function Pagination({
  page,
  totalPages,
  onChange,
}: {
  page: number
  totalPages: number
  onChange: (page: number) => void
}) {
  return (
    <div className="mt-5 flex items-center justify-between text-sm">
      <button
        className="rounded-lg border border-slate-300 px-3 py-2 disabled:opacity-40 dark:border-white/10"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
      >
        Previous
      </button>
      <span className="text-slate-500">
        Page {page} of {totalPages}
      </span>
      <button
        className="rounded-lg border border-slate-300 px-3 py-2 disabled:opacity-40 dark:border-white/10"
        disabled={page >= totalPages}
        onClick={() => onChange(page + 1)}
      >
        Next
      </button>
    </div>
  )
}
