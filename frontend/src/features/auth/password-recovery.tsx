import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { useLocale, useTranslations } from 'use-intl'
import { useSession } from './session'
import { apiJson, ApiClientError } from '@/shared/api/client'
import { ERROR_CODES, type ErrorCode } from '@/shared/api/errors'
import { Brand } from '@/shared/ui/brand'
import { LanguageSwitcher } from '@/shared/i18n/language-switcher'
import { Button } from '@/shared/ui/button'

export function PasswordRecovery({ reset = false }: { reset?: boolean }) {
  const t = useTranslations(), locale = useLocale(), navigate = useNavigate()
  const { user, logout } = useSession()
  const [link] = useState(() => {
    const params = new URLSearchParams(window.location.hash.slice(1))
    return { userId: params.get('userId') ?? '', token: params.get('token') ?? '' }
  })
  const valid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(link.userId) && /^[A-Za-z0-9_-]{20,128}$/.test(link.token)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [busy, setBusy] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<ErrorCode | ''>('')
  const [mismatch, setMismatch] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (busy || success || (reset && !valid)) return
    setError(''); setMismatch(false)
    if (reset && password !== confirmation) { setMismatch(true); return }
    setBusy(true)
    try {
      await apiJson(`/api/auth/password/${reset ? 'reset' : 'request'}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(reset ? { ...link, password, locale } : { email, locale }),
      })
      if (reset) { window.history.replaceState(null, '', window.location.pathname); setPassword(''); setConfirmation('') }
      setSuccess(true)
    } catch (failure) { setError(failure instanceof ApiClientError ? failure.code : ERROR_CODES.authServiceUnavailable) }
    finally { setBusy(false) }
  }
  async function signIn() {
    setBusy(true); setError('')
    try { if (user) await logout(); void navigate('/login', { replace: true }) }
    catch { setError(ERROR_CODES.authServiceUnavailable) }
    finally { setBusy(false) }
  }
  const inputClass = 'mt-2 h-10 w-full rounded-lg border border-input bg-background px-3 text-sm focus-visible:outline-2 focus-visible:outline-ring'
  return <main className="auth-shell"><section className="auth-access">
    <div className="auth-access-header"><Brand /><LanguageSwitcher /></div>
    <div className="auth-form-surface">
      <h1>{t(success ? (reset ? 'auth.passwordChanged' : 'auth.recoveryRequested') : (reset ? 'auth.resetPassword' : 'auth.forgotPassword'))}</h1>
      <p className="mt-3">{t(success ? (reset ? 'auth.passwordChangedDescription' : 'auth.recoveryNeutral') : (reset ? 'auth.resetDescription' : 'auth.recoveryDescription'))}</p>
      {user && <p className="mt-4" role="status">{t('auth.recoverySessionNotice', { email: user.email })}</p>}
      {error && <p className="mt-4" role="alert">{t(error)}</p>}
      {success ? <Button className="mt-6 w-full" disabled={busy} onClick={() => { void signIn() }}>{t(user ? 'auth.signOutAndSignIn' : 'auth.signIn')}</Button> : <form className="mt-6 space-y-5" onSubmit={submit}>
        {reset ? <>
          {!valid && <p role="alert">{t('errors.passwordRecoveryInvalid')}</p>}
          <div><label htmlFor="recovery-password">{t('auth.newPassword')}</label><input id="recovery-password" type="password" autoComplete="new-password" required minLength={8} maxLength={4096} className={inputClass} value={password} onChange={e => setPassword(e.target.value)} disabled={busy || !valid} /></div>
          <div><label htmlFor="recovery-confirmation">{t('auth.confirmPassword')}</label><input id="recovery-confirmation" type="password" autoComplete="new-password" required minLength={8} maxLength={4096} className={inputClass} value={confirmation} onChange={e => setConfirmation(e.target.value)} disabled={busy || !valid} /></div>
          {mismatch && <p role="alert">{t('auth.passwordMismatch')}</p>}
        </> : <div><label htmlFor="recovery-email">{t('auth.emailLabel')}</label><input id="recovery-email" type="email" autoComplete="email" required maxLength={320} className={inputClass} value={email} onChange={e => setEmail(e.target.value)} disabled={busy} /></div>}
        <Button className="h-auto min-h-10 w-full whitespace-normal py-2" type="submit" disabled={busy || (reset && !valid)}>{t(busy ? 'auth.recoverySubmitting' : (reset ? 'auth.changePassword' : 'auth.sendRecovery'))}</Button>
      </form>}
      {!success && <Link className="mt-5 inline-block underline" to={reset ? '/forgot-password' : '/login'}>{t(reset ? 'auth.requestRecoveryAgain' : 'auth.signIn')}</Link>}
    </div>
  </section></main>
}
