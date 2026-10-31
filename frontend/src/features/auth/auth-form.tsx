import { Brand } from '@/shared/ui/brand'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { useSession } from './session'
import { publicDestination } from '@/shared/config/navigation'
import { useLocale, useTranslations } from 'use-intl'
import { useState } from 'react'
import { LockKeyhole, Mail } from 'lucide-react'
import { LanguageSwitcher } from '@/shared/i18n/language-switcher'
import { Button } from '@/shared/ui/button'
import { ERROR_CODES, assertErrorCode, type ErrorCode } from '@/shared/api/errors'

type AuthMode = 'login' | 'register'

interface AuthFormProps {
  mode: AuthMode
}

async function readErrorMessage(response: Response) {
  let body: unknown

  try {
    body = await response.json()
  } catch (error) {
    console.error(
      JSON.stringify({
        event: 'auth_error_body_invalid',
        status: response.status,
        message: error instanceof Error ? error.message : 'Unknown JSON parse error',
      }),
    )
    return ERROR_CODES.requestFailed
  }

  if (
    body &&
    typeof body === 'object' &&
    !Array.isArray(body) &&
    typeof (body as Record<string, unknown>).error === 'string'
  ) {
    return assertErrorCode((body as Record<string, string>).error)
  }

  return ERROR_CODES.requestFailed
}

export function AuthForm({ mode }: AuthFormProps) {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const { authenticated } = useSession()
  const t = useTranslations()
  const locale = useLocale()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<ErrorCode | ''>('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const isRegister = mode === 'register'
  const title = isRegister ? t('auth.registerTitle') : t('auth.loginTitle')
  const description = isRegister
    ? t('auth.registerDescription')
    : t('auth.loginDescription')
  const endpoint = isRegister ? '/api/auth/register' : '/api/auth/login'

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')

    if (!email.trim()) {
      setError(ERROR_CODES.emailRequired)
      return
    }
    if (!password) {
      setError(ERROR_CODES.passwordRequired)
      return
    }

    setIsSubmitting(true)

    let response: Response
    try {
      response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, locale }),
      })
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'auth_submit_failed',
          mode,
          message: error instanceof Error ? error.message : 'Unknown auth error',
        }),
      )
      setError(ERROR_CODES.authServiceUnavailable)
      return
    } finally {
      setIsSubmitting(false)
    }

    if (!response.ok) {
      setError(await readErrorMessage(response))
      return
    }

    const result = await response.json()
    authenticated(result.user, result.emailConfirmation)
    void navigate(publicDestination(params.get('returnTo')), { replace: true })
  }

  return <main className="auth-shell">
    <section className="auth-access">
      <div className="auth-access-header"><Brand /><LanguageSwitcher /></div>
      <div className="auth-form-surface">
        <h1>{title}</h1><p>{description}</p>
          <form onSubmit={submit} className="mt-6 flex flex-col gap-4">
            <div>
              <label
                htmlFor="auth-email"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                {t('auth.emailLabel')}
              </label>
              <div className="relative">
                <Mail
                  className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
                  aria-hidden="true"
                />
                <input
                  id="auth-email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="w-full rounded-lg border border-input bg-background py-2 pr-3 pl-9 text-sm text-foreground outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40"
                  placeholder={t('auth.emailPlaceholder')}
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="auth-password"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                {t('auth.passwordLabel')}
              </label>
              <div className="relative">
                <LockKeyhole
                  className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
                  aria-hidden="true"
                />
                <input
                  id="auth-password"
                  type="password"
                  autoComplete={isRegister ? 'new-password' : 'current-password'}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="w-full rounded-lg border border-input bg-background py-2 pr-3 pl-9 text-sm text-foreground outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40"
                  placeholder={t('auth.passwordPlaceholder')}
                />
              </div>
            </div>

            {error && (
              <p role="alert" className="rounded-lg bg-outscope-soft px-3 py-2 text-sm text-outscope-text">
                {t(error)}
              </p>
            )}

            <Button type="submit" className="h-10 w-full" disabled={isSubmitting}>
              {isSubmitting
                ? isRegister
                  ? t('auth.creatingAccount')
                  : t('auth.signingIn')
                : isRegister
                  ? t('auth.createAccount')
                  : t('auth.signIn')}
            </Button>
          </form>
          {!isRegister && <Link to="/forgot-password" className="mt-5 inline-block text-sm underline">{t('auth.forgotPassword')}</Link>}

          <p className="mt-5 text-center text-sm text-muted-foreground">
            {isRegister
              ? t('auth.alreadyHaveAccount')
              : t('auth.dontHaveAccount')}{' '}
            <Link
              to={`${isRegister ? '/login' : '/register'}${params.toString() ? '?' + params : ''}`}
              className="font-medium text-foreground underline-offset-4 hover:underline"
            >
              {isRegister ? t('auth.signIn') : t('auth.createOne')}
            </Link>
          </p>
      </div>
    </section>
  </main>
}
