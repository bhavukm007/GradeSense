import { Menu, Moon, Sun } from 'lucide-react'

import { useThemeStore } from '../../stores/themeStore'

interface TopNavigationProps {
  onOpenSidebar: () => void
}

export function TopNavigation({ onOpenSidebar }: TopNavigationProps) {
  const { theme, toggleTheme } = useThemeStore()

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-slate-50/80 backdrop-blur-xl dark:border-white/[0.07] dark:bg-ink-950/80">
      <a
        href="#main-content"
        className="sr-only z-50 rounded-lg bg-cyan-500 px-4 py-2 font-semibold text-ink-950 focus:not-sr-only focus:absolute focus:left-4 focus:top-3"
      >
        Skip to content
      </a>
      <div className="flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8 xl:px-10">
        <div className="flex items-center gap-3">
          <button
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-200 dark:text-slate-400 dark:hover:bg-white/10 lg:hidden"
            onClick={onOpenSidebar}
            aria-label="Open navigation"
          >
            <Menu className="size-5" />
          </button>
          <div>
            <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
              GradeSense Operations
            </p>
            <p className="hidden text-xs text-slate-500 sm:block">Decision support workspace</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 shadow-sm dark:border-white/10 dark:bg-white/5 dark:text-slate-400 sm:flex">
            <span className="size-1.5 rounded-full bg-emerald-400" />
            System ready
          </span>
          <button
            onClick={toggleTheme}
            className="grid size-9 place-items-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:-translate-y-0.5 dark:border-white/10 dark:bg-white/5 dark:text-slate-300"
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          >
            {theme === 'dark' ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </button>
          <div className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-slate-700 to-slate-900 text-xs font-semibold text-white shadow-sm">
            GS
          </div>
        </div>
      </div>
    </header>
  )
}
