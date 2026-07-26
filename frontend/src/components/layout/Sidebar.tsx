import {
  Activity,
  BarChart3,
  Binary,
  FlaskConical,
  Gauge,
  Grid3X3,
  History,
  Lightbulb,
  Sparkles,
  Settings,
  ShieldCheck,
  Download,
  X,
} from 'lucide-react'
import { NavLink } from 'react-router'

const navigation = [
  { label: 'Dashboard', to: '/dashboard', icon: Gauge },
  { label: 'Prediction Center', to: '/prediction', icon: Activity },
  { label: 'Recommendations', to: '/recommendations', icon: Lightbulb },
  { label: 'What-if Simulator', to: '/simulator', icon: FlaskConical },
  { label: 'Dataset Analytics', to: '/analytics', icon: BarChart3 },
  { label: 'Correlations', to: '/correlations', icon: Grid3X3 },
  { label: 'Prediction History', to: '/history/predictions', icon: History },
  { label: 'Recommendation History', to: '/history/recommendations', icon: History },
  { label: 'Model Information', to: '/model', icon: Binary },
  { label: 'System Status', to: '/status', icon: Activity },
  { label: 'Model Registry', to: '/admin/models', icon: Binary },
  { label: 'System Metrics', to: '/admin/metrics', icon: Gauge },
  { label: 'Audit Log', to: '/admin/audit', icon: ShieldCheck },
  { label: 'Configuration', to: '/admin/config', icon: Settings },
  { label: 'Health Dashboard', to: '/admin/health', icon: Activity },
  { label: 'Export Center', to: '/admin/exports', icon: Download },
]

interface SidebarProps {
  open: boolean
  onClose: () => void
}

export function Sidebar({ open, onClose }: SidebarProps) {
  return (
    <>
      {open && (
        <button
          aria-label="Close navigation"
          className="fixed inset-0 z-40 bg-slate-950/70 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-[280px] flex-col border-r border-white/10 bg-ink-950 px-4 py-5 text-slate-100 transition-transform lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between px-3">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-gradient-to-br from-cyan-400 to-blue-500 shadow-lg shadow-cyan-500/20">
              <Sparkles className="size-5 text-ink-950" />
            </div>
            <div>
              <p className="font-semibold tracking-tight">
                GradeSense<span className="text-cyan-400">AI</span>
              </p>
              <p className="text-[10px] font-medium uppercase tracking-[0.18em] text-slate-500">
                Process Intelligence
              </p>
            </div>
          </div>
          <button className="rounded-lg p-2 text-slate-400 lg:hidden" onClick={onClose}>
            <X className="size-5" />
          </button>
        </div>

        <nav className="mt-10 flex-1 space-y-1" aria-label="Primary navigation">
          <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-600">
            Workspace
          </p>
          {navigation.map(({ label, to, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={onClose}
              className={({ isActive }) =>
                `group flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition ${
                  isActive
                    ? 'bg-white/10 text-white shadow-sm'
                    : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className={`size-[18px] ${isActive ? 'text-cyan-400' : ''}`} />
                  {label}
                  {isActive && <span className="ml-auto size-1.5 rounded-full bg-cyan-400" />}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
            <span className="size-2 rounded-full bg-emerald-400 shadow-[0_0_10px_#34d399]" />
            Intelligence online
          </div>
          <p className="mt-2 text-xs leading-5 text-slate-500">Submission candidate - v0.2.0</p>
        </div>
      </aside>
    </>
  )
}
