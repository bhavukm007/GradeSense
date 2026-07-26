import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { type PropsWithChildren, useState } from 'react'
import { BrowserRouter } from 'react-router'

import { ApiError } from '../api/client'
import { useThemeStore } from '../stores/themeStore'

function ThemeProvider({ children }: PropsWithChildren) {
  const theme = useThemeStore((state) => state.theme)
  return (
    <div className={theme === 'dark' ? 'dark' : ''}>
      <div className="min-h-screen bg-slate-50 text-slate-950 antialiased dark:bg-ink-950 dark:text-slate-100">
        {children}
      </div>
    </div>
  )
}

export function AppProviders({ children }: PropsWithChildren) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: (failureCount, error) =>
              failureCount < 2 &&
              (!(error instanceof ApiError) || !error.status || error.status >= 500),
            retryDelay: (attempt) => Math.min(1_500 * 2 ** attempt, 5_000),
            refetchOnWindowFocus: false,
          },
        },
      }),
  )

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider>{children}</ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
