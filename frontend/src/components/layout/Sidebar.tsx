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
  Presentation,
  Download,
  X,
} from 'lucide-react'
import { NavLink } from 'react-router'

const navigation = [
  {
    label: 'Operations',
    items: [
      { label: 'Dashboard', to: '/dashboard', icon: Gauge },
      { label: 'Demo Workspace', to: '/demo-workspace', icon: Presentation },
      { label: 'Prediction Center', to: '/prediction', icon: Activity },
      { label: 'Recommendations', to: '/recommendations', icon: Lightbulb },
      { label: 'What-if Simulator', to: '/simulator', icon: FlaskConical },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { label: 'Dataset Analytics', to: '/analytics', icon: BarChart3 },
      { label: 'Correlations', to: '/correlations', icon: Grid3X3 },
      { label: 'Prediction History', to: '/history/predictions', icon: History },
      { label: 'Recommendation History', to: '/history/recommendations', icon: History },
      { label: 'Model Information', to: '/model', icon: Binary },
    ],
  },
  {
    label: 'Platform',
    items: [
      { label: 'System Status', to: '/status', icon: Activity },
      { label: 'Model Registry', to: '/admin/models', icon: Binary },
      { label: 'System Metrics', to: '/admin/metrics', icon: Gauge },
      { label: 'Audit Log', to: '/admin/audit', icon: ShieldCheck },
      { label: 'Configuration', to: '/admin/config', icon: Settings },
      { label: 'Health Dashboard', to: '/admin/health', icon: Activity },
      { label: 'Export Center', to: '/admin/exports', icon: Download },
    ],
  },
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
        aria-label="GradeSense navigation"
        className={`fixed inset-y-0 left-0 z-50 flex w-[272px] flex-col overflow-hidden border-r border-white/10 bg-ink-950 text-slate-100 shadow-2xl transition-transform lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 lg:shadow-none ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex shrink-0 items-center justify-between px-5 pb-5 pt-5">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl bg-gradient-to-br from-cyan-400 to-blue-500 shadow-lg shadow-cyan-500/20">
              <Sparkles className="size-5 text-ink-950" />
            </div>
            <div>
              <p className="font-semibold tracking-tight">GradeSense</p>
              <p className="text-[10px] font-medium uppercase tracking-[0.18em] text-slate-500">
                Process Intelligence
              </p>
            </div>
          </div>
          <button
            className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white lg:hidden"
            onClick={onClose}
            aria-label="Close navigation"
          >
            <X className="size-5" />
          </button>
        </div>

        <nav
          className="min-h-0 flex-1 space-y-5 overflow-y-auto overscroll-contain px-3 pb-4 pt-2"
          aria-label="Primary navigation"
        >
          {navigation.map((section) => (
            <div key={section.label}>
              <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-600">
                {section.label}
              </p>
              <div className="space-y-0.5">
                {section.items.map(({ label, to, icon: Icon }) => (
                  <NavLink
                    key={to}
                    to={to}
                    onClick={onClose}
                    className={({ isActive }) =>
                      `group flex min-h-10 items-center gap-3 rounded-xl px-3 py-2 text-[13px] font-medium ${
                        isActive
                          ? 'bg-white/10 text-white shadow-sm'
                          : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <Icon
                          aria-hidden="true"
                          className={`size-[17px] shrink-0 ${isActive ? 'text-cyan-400' : ''}`}
                        />
                        <span className="min-w-0 flex-1 leading-5">{label}</span>
                        {isActive && (
                          <span
                            aria-hidden="true"
                            className="size-1.5 shrink-0 rounded-full bg-cyan-400"
                          />
                        )}
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="m-4 mt-2 shrink-0 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
            <span className="size-2 rounded-full bg-emerald-400 shadow-[0_0_10px_#34d399]" />
            Intelligence online
          </div>
          <p className="mt-2 text-xs leading-5 text-slate-500">Industrial AI platform · v0.2.0</p>
        </div>
      </aside>
    </>
  )
}
