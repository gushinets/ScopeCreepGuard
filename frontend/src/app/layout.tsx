import { useState } from 'react'
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router'
import { useTranslations } from 'use-intl'
import { LogOut, ShieldCheck } from 'lucide-react'
import { useSession, ProductSession } from '@/features/auth'
import { useProjects } from '@/features/projects'
import { SaveFeedback, useDrafts } from '@/features/drafts'
import { LanguageSwitcher } from '@/shared/i18n/language-switcher'
import { useWorkspaceNavigation } from '@/shared/ui/navigation'
import { cn } from '@/shared/ui/utils'
import { publicDestination } from '@/shared/config/navigation'
import { WorkspaceProvider } from './workspace'

export function ProtectedWorkspace() {
  const { user, loading, error, refresh } = useSession()
  const location = useLocation()
  const t = useTranslations()
  if (loading) return <main className="p-10" role="status">{t('workspace.loadingTitle')}</main>
  if (error && !user) return <main className="p-10"><p role="alert">{t(error)}</p><button onClick={() => { void refresh().catch(() => {}) }}>{t('drafts.retry')}</button></main>
  if (!user) return <Navigate to={`/login?returnTo=${encodeURIComponent(location.pathname + location.search + location.hash)}`} replace />
  return <WorkspaceProvider key={user.id}><WorkspaceLayout /></WorkspaceProvider>
}

export function PublicAuthLayout() {
  const { user, loading } = useSession()
  const location = useLocation()
  if (loading) return null
  if (user) return <Navigate to={publicDestination(new URLSearchParams(location.search).get('returnTo'))} replace />
  return <Outlet />
}

function WorkspaceLayout() {
  const { user, logout, error: sessionError, refresh } = useSession()
  const { view, setView, beforeLeave } = useWorkspaceNavigation()
  const { isLoadingProjects, projectError } = useProjects()
  const { saveDraft, currentDraftId } = useDrafts()
  const navigate = useNavigate()
  const t = useTranslations()
  const [loggingOut, setLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState(false)
  const active = view === 'new_project' || view === 'edit_project' ? 'projects' : view
  async function leave() {
    setLoggingOut(true); setLogoutError(false)
    try { await beforeLeave(); if (currentDraftId) await saveDraft(); await logout(); void navigate('/login', { replace: true }) }
    catch { setLogoutError(true); setLoggingOut(false) }
  }
  return <div className="min-h-screen bg-background text-foreground"><ProductSession />
    <header className="sticky top-0 z-10 border-b border-border bg-background/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <div className="flex items-center gap-2.5"><span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground"><ShieldCheck className="size-5" aria-hidden="true" /></span><div className="leading-tight"><p className="text-sm font-semibold">{t('brand.name')}</p><p className="text-xs text-muted-foreground">{t('brand.prototype')}</p></div></div>
        <div className="flex min-w-0 items-center gap-3"><nav aria-label={t('nav.primary')} className="flex min-w-0 items-center gap-1 overflow-x-auto">
          {(['check', 'projects', 'history', 'drafts'] as const).map(page => <button key={page} type="button" onClick={() => setView(page)} aria-current={active === page ? 'page' : undefined} className={cn('shrink-0 whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-ring', active === page ? 'bg-muted text-foreground' : 'text-muted-foreground hover:bg-muted/60')}>{t(`nav.${page}`)}</button>)}
        </nav><div className="hidden h-6 w-px bg-border sm:block" /><LanguageSwitcher /><div className="hidden max-w-44 truncate text-xs text-muted-foreground md:block">{user?.email}</div>
          <button type="button" onClick={() => { void leave() }} disabled={loggingOut} className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm text-muted-foreground hover:bg-muted/60 disabled:opacity-50"><LogOut className="size-4" aria-hidden="true" /><span className="hidden sm:inline">{t(loggingOut ? 'nav.loggingOut' : 'nav.logout')}</span></button>
        </div>
      </div>
    </header>
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      {sessionError && <div role="alert"><p>{t(sessionError)}</p><button onClick={() => { void refresh().catch(() => {}) }}>{t('drafts.retry')}</button></div>}
      {logoutError && <p role="alert">{t('errors.requestFailed')}</p>}
      {isLoadingProjects ? <div className="rounded-xl border border-border bg-card/50 p-10 text-center"><p>{t('workspace.loadingTitle')}</p><p className="mt-1 text-sm text-muted-foreground">{t('workspace.loadingDescription')}</p></div> : projectError ? <p role="alert">{t(projectError)}</p> : <><SaveFeedback /><Outlet /></>}
    </main>
    <footer className="mx-auto max-w-6xl px-4 pb-10 sm:px-6"><p className="border-t border-border pt-4 text-xs leading-relaxed text-muted-foreground">{t('workspace.footer')}</p></footer>
  </div>
}
