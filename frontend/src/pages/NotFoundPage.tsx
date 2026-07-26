import { ArrowLeft } from 'lucide-react'
import { Link } from 'react-router'

export function NotFoundPage() {
  return (
    <main className="grid min-h-screen place-items-center px-6">
      <div className="text-center">
        <p className="text-sm font-semibold text-cyan-500">404</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight">Workspace not found</h1>
        <p className="mt-3 text-sm text-slate-500">
          The requested GradeSenseAI page does not exist.
        </p>
        <Link
          className="mt-7 inline-flex items-center gap-2 text-sm font-medium text-cyan-500"
          to="/dashboard"
        >
          <ArrowLeft className="size-4" /> Return to dashboard
        </Link>
      </div>
    </main>
  )
}
