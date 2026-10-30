import { useState } from 'react'
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router'
import { useTranslations } from 'use-intl'
import { LogOut, ScanLine, FolderOpen, History, FilePenLine, Menu, X, ChevronRight } from 'lucide-react'
import { useSession, ProductSession } from '@/features/auth'
import { useProjects } from '@/features/projects'
import { SaveFeedback, useDrafts } from '@/features/drafts'
import { LanguageSwitcher } from '@/shared/i18n/language-switcher'
import { useWorkspaceNavigation } from '@/shared/ui/navigation'
import { Brand } from '@/shared/ui/brand'
import { publicDestination } from '@/shared/config/navigation'
import { WorkspaceProvider } from './workspace'
import { OnboardingProvider, SkipOnboarding, OnboardingGuide } from '@/features/onboarding'

export function ProtectedWorkspace() {
  const { user, loading, error, refresh } = useSession()
  const location = useLocation()
  const t = useTranslations()
  if (loading) return <main className="p-10" role="status">{t('workspace.loadingTitle')}</main>
  if (error && (!user || user.workspaceAccess === 'email_confirmation_required')) return <main className="p-10"><p role="alert">{t(error)}</p><button onClick={() => { void refresh().catch(() => {}) }}>{t('drafts.retry')}</button></main>
  if (!user) return <Navigate to={`/login?returnTo=${encodeURIComponent(location.pathname + location.search + location.hash)}`} replace />
  if (user.workspaceAccess === 'email_confirmation_required') return <Navigate to={`/verify-email?returnTo=${encodeURIComponent(publicDestination(location.pathname + location.search + location.hash))}`} replace />
  return <OnboardingProvider key={user.id}><WorkspaceProvider key={user.id}><WorkspaceLayout /></WorkspaceProvider></OnboardingProvider>
}

export function PublicAuthLayout() {
  const { user, loading, error, refresh } = useSession()
  const t = useTranslations()
  const location = useLocation()
  if (loading) return null
  if (error) return <main className="auth-shell"><p role="alert">{t(error)}</p><button onClick={() => { void refresh().catch(() => {}) }}>{t('drafts.retry')}</button></main>
  if (user?.workspaceAccess === 'email_confirmation_required') return <Navigate to={`/verify-email?returnTo=${encodeURIComponent(publicDestination(new URLSearchParams(location.search).get('returnTo')))}`} replace />
  if (user) return <Navigate to={publicDestination(new URLSearchParams(location.search).get('returnTo'))} replace />
  return <Outlet />
}

function WorkspaceLayout() {
  const { user, logout, error: sessionError, refresh } = useSession()
  const { view, setView, beforeLeave } = useWorkspaceNavigation()
  const { isLoadingProjects, projectError, selectedProject } = useProjects()
  const { saveDraft, currentDraftId } = useDrafts()
  const navigate = useNavigate()
  const t = useTranslations()
  const [menuOpen, setMenuOpen] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState(false)
  const active = view === 'new_project' || view === 'edit_project' ? 'projects' : view
  async function leave() {
    setLoggingOut(true); setLogoutError(false)
    try { await beforeLeave(); if (currentDraftId) await saveDraft(); await logout(); void navigate('/login', { replace: true }) }
    catch { setLogoutError(true); setLoggingOut(false) }
  }
  const icons = { check: ScanLine, projects: FolderOpen, history: History, drafts: FilePenLine }
  return <div className="workspace-shell"><ProductSession />
    <aside className="workspace-navigation" id="workspace-menu" data-open={menuOpen}>
      <div className="workspace-navigation-inner">
        <Brand />
        <SkipOnboarding />
        <nav aria-label={t('nav.primary')} className="workspace-nav-links">
          {(['check', 'projects', 'history', 'drafts'] as const).map(page => {
            const Icon = icons[page]
            return <button key={page} type="button" onClick={() => { setView(page); setMenuOpen(false) }} aria-current={active === page ? 'page' : undefined}><Icon aria-hidden="true" />{t(`nav.${page}`)}</button>
          })}
        </nav>
        <div className="workspace-account">
          <p className="workspace-account-email">{user?.email}</p>
          <button type="button" onClick={() => { void leave() }} disabled={loggingOut} className="inline-flex items-center gap-2 text-sm text-muted-foreground disabled:opacity-60"><LogOut size={16} aria-hidden="true" />{t(loggingOut ? 'nav.loggingOut' : 'nav.logout')}</button>
        </div>
      </div>
    </aside>
    <header className="workspace-topbar">
      <button className="mobile-menu-button" type="button" aria-label={t(menuOpen ? 'design.closeMenu' : 'design.openMenu')} aria-expanded={menuOpen} aria-controls="workspace-menu" onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X size={20} /> : <Menu size={20} />}</button>
      <span className="mobile-brand"><Brand compact /></span><div className="workspace-breadcrumb"><span>{t('design.workspace')}</span><ChevronRight size={14} aria-hidden="true" /><strong>{t(`nav.${active}`)}</strong>{selectedProject && view !== 'history' && <span className="breadcrumb-project"><ChevronRight size={14} aria-hidden="true" /><strong>{selectedProject.name}</strong></span>}</div>
      <LanguageSwitcher />
    </header>
    <div className="mobile-guidance"><SkipOnboarding /></div>
    <div className="workspace-content">
      <main className="workspace-main">
        {sessionError && <div role="alert"><p>{t(sessionError)}</p><button onClick={() => { void refresh().catch(() => {}) }}>{t('drafts.retry')}</button></div>}
        {logoutError && <p role="alert">{t('errors.requestFailed')}</p>}
        {isLoadingProjects ? <div className="panel"><p role="status">{t('workspace.loadingTitle')}</p></div> : projectError ? <p role="alert">{t(projectError)}</p> : <><SaveFeedback /><Outlet /></>}
      </main>
      <footer className="workspace-footer"><p>{t('workspace.footer')}</p></footer>
    </div>
    <OnboardingGuide />
  </div>
}
