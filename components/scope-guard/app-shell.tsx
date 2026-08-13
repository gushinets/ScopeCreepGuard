'use client'

import { useState } from 'react'
import { LogOut, ShieldCheck } from 'lucide-react'
import { cn } from '@/lib/utils'
import { StoreProvider, useStore, type View } from './store'
import { ScopeCheckView } from './scope-check-view'
import { ProjectsView } from './projects-view'
import { NewProjectView } from './new-project-view'
import { HistoryView } from './history-view'

const NAV: { id: View; label: string }[] = [
  { id: 'check', label: 'Scope check' },
  { id: 'projects', label: 'Projects' },
  { id: 'history', label: 'History' },
]

function Header() {
  const { view, setView, user, logout } = useStore()
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const activeNav: View = view === 'new_project' ? 'projects' : view

  async function handleLogout() {
    setIsLoggingOut(true)
    try {
      await logout()
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'logout_failed',
          message: error instanceof Error ? error.message : 'Unknown logout error',
        }),
      )
      setIsLoggingOut(false)
    }
  }

  return (
    <header className="sticky top-0 z-10 border-b border-border bg-background/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <div className="flex items-center gap-2.5">
          <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <ShieldCheck className="size-5" aria-hidden="true" />
          </span>
          <div className="leading-tight">
            <p className="text-sm font-semibold text-foreground">
              Scope Creep Guard
            </p>
            <p className="text-xs text-muted-foreground">Prototype</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <nav aria-label="Primary" className="flex items-center gap-1">
            {NAV.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setView(item.id)}
                aria-current={activeNav === item.id ? 'page' : undefined}
                className={cn(
                  'rounded-lg px-3 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  activeNav === item.id
                    ? 'bg-muted text-foreground'
                    : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground',
                )}
              >
                {item.label}
              </button>
            ))}
          </nav>

          <div className="hidden h-6 w-px bg-border sm:block" />

          <div className="hidden max-w-44 truncate text-xs text-muted-foreground md:block">
            {user?.email}
          </div>
          <button
            type="button"
            onClick={handleLogout}
            disabled={isLoggingOut}
            className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted/60 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
          >
            <LogOut className="size-4" aria-hidden="true" />
            <span className="hidden sm:inline">
              {isLoggingOut ? 'Logging out...' : 'Logout'}
            </span>
          </button>
        </div>
      </div>
    </header>
  )
}

function Body() {
  const { view, isLoadingProjects, projectError } = useStore()

  if (isLoadingProjects) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <div className="rounded-xl border border-border bg-card/50 p-10 text-center">
          <p className="text-sm font-medium text-foreground">Loading workspace...</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Fetching your private projects and history.
          </p>
        </div>
      </main>
    )
  }

  if (projectError) {
    return (
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <div className="rounded-xl border border-outscope-border bg-outscope-soft p-10 text-center">
          <p className="text-sm font-medium text-outscope-text">{projectError}</p>
        </div>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      {view === 'check' && <ScopeCheckView />}
      {view === 'projects' && <ProjectsView />}
      {view === 'new_project' && <NewProjectView />}
      {view === 'history' && <HistoryView />}
    </main>
  )
}

export function AppShell() {
  return (
    <StoreProvider>
      <div className="min-h-screen bg-background text-foreground">
        <Header />
        <Body />
        <footer className="mx-auto max-w-6xl px-4 pb-10 sm:px-6">
          <p className="border-t border-border pt-4 text-xs leading-relaxed text-muted-foreground">
            Scope Creep Guard stores projects and history in your authenticated
            workspace. Client requests are not analyzed by a real AI or sent
            anywhere. Verdicts are AI-assisted suggestions, not legal advice.
          </p>
        </footer>
      </div>
    </StoreProvider>
  )
}
