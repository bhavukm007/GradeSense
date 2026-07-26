import { useState } from 'react'
import { Outlet } from 'react-router'

import { Sidebar } from './Sidebar'
import { TopNavigation } from './TopNavigation'

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[272px_minmax(0,1fr)]">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="min-w-0">
        <TopNavigation onOpenSidebar={() => setSidebarOpen(true)} />
        <main
          id="main-content"
          className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-6 sm:py-8 lg:px-8 xl:px-10"
        >
          <Outlet />
        </main>
      </div>
    </div>
  )
}
