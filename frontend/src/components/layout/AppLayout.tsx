import { useState } from 'react'
import { Outlet } from 'react-router'

import { Sidebar } from './Sidebar'
import { TopNavigation } from './TopNavigation'

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[280px_1fr]">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="min-w-0">
        <TopNavigation onOpenSidebar={() => setSidebarOpen(true)} />
        <main className="mx-auto max-w-[1600px] px-5 py-8 sm:px-8 lg:px-10 lg:py-10">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
