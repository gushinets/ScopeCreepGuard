import { useEffect, useState, type ReactNode } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router'
import { useLocale, useTranslations } from 'use-intl'
import { useSession, type EmailConfirmation } from './session'
import { apiJson, ApiClientError } from '@/shared/api/client'
import { ERROR_CODES, type ErrorCode } from '@/shared/api/errors'
import { publicDestination } from '@/shared/config/navigation'
import { Brand } from '@/shared/ui/brand'
import { LanguageSwitcher } from '@/shared/i18n/language-switcher'
import { Button } from '@/shared/ui/button'

function EmailShell({ children }: { children: ReactNode }) {
  return <main className="auth-shell"><section className="auth-access"><div className="auth-access-header"><Brand /><LanguageSwitcher /></div><div className="auth-form-surface">{children}</div></section></main>
}

export function VerifyEmail() {
  const { user, loading, error: sessionError, emailConfirmation, refresh, logout } = useSession()
  const t = useTranslations(), locale = useLocale(), navigate = useNavigate()
  const [params] = useSearchParams()
  const destination = publicDestination(params.get('returnTo'))
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<ErrorCode | ''>('')
  const [attempt, setAttempt] = useState<EmailConfirmation>()
  const [until, setUntil] = useState(0)
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const interval = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(interval)
  }, [])
  const [serverObservedAt, setServerObservedAt] = useState(() => Date.now())
  useEffect(() => { setServerObservedAt(Date.now()); setAttempt(undefined) }, [emailConfirmation])
  const remaining = Math.max(0, Math.ceil((Math.max(until, (emailConfirmation?.retryAfter ? serverObservedAt + emailConfirmation.retryAfter * 1000 : 0)) - now) / 1000))
  async function resend() {
    setSending(true); setError('')
    try {
      const result = await apiJson<{ emailConfirmation: EmailConfirmation }>('/api/auth/email/resend', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ locale }) })
      setAttempt(result.emailConfirmation)
      setUntil(Date.now() + result.emailConfirmation.retryAfter * 1000)
    } catch (failure) {
      setError(failure instanceof ApiClientError ? failure.code : ERROR_CODES.authServiceUnavailable)
      if (!(failure instanceof ApiClientError) || failure.status >= 500) setAttempt({ status: 'unknown', retryAfter: 0 })
      if (failure instanceof ApiClientError && failure.status === 401) await refresh().catch(() => {})
      if (failure instanceof ApiClientError && failure.status === 429) {
        const seconds = Number(failure.headers.get('Retry-After'))
        if (Number.isFinite(seconds) && seconds > 0) setUntil(Date.now() + seconds * 1000)
      }
    } finally { setSending(false); setNow(Date.now()) }
  }
  async function signOut() {
    setSending(true); setError('')
    try { await logout(); void navigate('/login', { replace: true }) }
    catch { setError(ERROR_CODES.authServiceUnavailable); setSending(false) }
  }
  if (loading) return <EmailShell><p role="status">{t('workspace.loadingTitle')}</p></EmailShell>
  if (sessionError) return <EmailShell><p role="alert">{t(sessionError)}</p><Button onClick={() => { void refresh().catch(() => {}) }}>{t('drafts.retry')}</Button></EmailShell>
  if (!user) return <Navigate to={`/login?returnTo=${encodeURIComponent(destination)}`} replace />
  if (user.workspaceAccess === 'allowed') return <Navigate to={destination} replace />
  const status = attempt?.status ?? emailConfirmation?.status ?? 'unknown'
  return <EmailShell>
    <h1>{t('auth.verifyTitle')}</h1><p>{t('auth.verifyDescription')}</p>
    <p className="my-4 break-all font-medium">{user.email}</p>
    <p role="status" className="my-4">{t(`auth.mail_${status}`)}</p>
    {error && <p role="alert" className="my-4">{t(error)}</p>}
    <Button className="mt-4 h-auto min-h-10 w-full whitespace-normal py-2" disabled={sending || remaining > 0} onClick={() => { void resend() }}>{t(sending ? 'auth.sendingEmail' : 'auth.resendEmail')}</Button>
    {remaining > 0 && <p className="mt-3 text-sm">{t('auth.resendCountdown', { seconds: remaining })}</p>}
    <Button className="mt-4 h-auto min-h-10 w-full whitespace-normal py-2" variant="outline" disabled={sending} onClick={() => { void refresh().catch(() => {}) }}>{t('auth.checkConfirmation')}</Button>
    <button type="button" className="mt-5 w-full text-sm underline" disabled={sending} onClick={() => { void signOut() }}>{t('auth.signOutAndSignIn')}</button>
  </EmailShell>
}

export function ConfirmEmail() {
  const t = useTranslations()
  const { user, refresh, logout } = useSession()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const destination = publicDestination(params.get('returnTo'))
  // The fragment survives refresh, but is never copied to router/browser storage.
  const [link] = useState(() => {
    const fragment = new URLSearchParams(window.location.hash.slice(1))
    const userId = fragment.get('userId') ?? '', token = fragment.get('token') ?? ''
    return { userId, token, valid: /^[0-9a-f-]{36}$/i.test(userId) && token.length > 0 && token.length <= 512 }
  })
  const [busy, setBusy] = useState(false)
  const [success, setSuccess] = useState(false)
  const [canContinue, setCanContinue] = useState(false)
  const [error, setError] = useState<ErrorCode | ''>('')
  async function confirm() {
    if (!link.valid || busy || success) return
    setBusy(true); setError('')
    try {
      await apiJson('/api/auth/email/confirm', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ userId: link.userId, token: link.token }) })
      window.history.replaceState(null, '', window.location.pathname)
      setSuccess(true)
      try { const identity = await refresh(true); const allowed = identity?.id === link.userId && identity.workspaceAccess === 'allowed'; setCanContinue(allowed); if (allowed) void navigate(destination, { replace: true }) }
      catch { /* Confirmation succeeded; sign-in remains an available recovery path. */ }
    } catch (failure) { setError(failure instanceof ApiClientError ? failure.code : ERROR_CODES.authServiceUnavailable) }
    finally { setBusy(false) }
  }
  async function signIn() {
    setBusy(true); setError('')
    try { if (user) await logout(); void navigate('/login', { replace: true }) }
    catch { setError(ERROR_CODES.authServiceUnavailable); setBusy(false) }
  }
  if (success) return <EmailShell><h1>{t('auth.confirmedTitle')}</h1><p role="status">{t('auth.confirmedDescription')}</p>{canContinue ? <Link className="mt-5 inline-block underline" to={destination} replace>{t('auth.continueWorkspace')}</Link> : <><p className="mt-4">{t('auth.confirmedSignIn')}</p><Button className="mt-5 h-auto min-h-10 w-full whitespace-normal py-2" disabled={busy} onClick={() => { void signIn() }}>{t(user ? 'auth.signOutAndSignIn' : 'auth.signIn')}</Button>{error && <p role="alert">{t(error)}</p>}</>}</EmailShell>
  return <EmailShell><h1>{t('auth.confirmTitle')}</h1><p>{t('auth.confirmDescription')}</p>
    {(!link.valid || error) && <p role="alert" className="my-4">{t(error || 'errors.emailConfirmationInvalid')}</p>}
    <Button className="mt-5 h-auto min-h-10 w-full whitespace-normal py-2" disabled={!link.valid || busy} onClick={() => { void confirm() }}>{t(busy ? 'auth.confirming' : 'auth.confirmEmail')}</Button>
    <p className="mt-5 text-sm">{t('auth.newLinkHelp')}</p><Link className="mt-3 inline-block underline" to="/verify-email">{t('auth.requestNewLink')}</Link>
  </EmailShell>
}
