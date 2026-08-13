'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { LockKeyhole, Mail, ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'

type AuthMode = 'login' | 'register'

interface AuthFormProps {
  mode: AuthMode
}

async function readErrorMessage(response: Response) {
  try {
    const body = await response.json()
    if (body && typeof body.error === 'string') return body.error
  } catch (error) {
    console.error(
      JSON.stringify({
        event: 'auth_error_body_invalid',
        status: response.status,
        message: error instanceof Error ? error.message : 'Unknown JSON parse error',
      }),
    )
  }
  return 'The request failed. Please try again.'
}

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const isRegister = mode === 'register'
  const title = isRegister ? 'Create your workspace' : 'Welcome back'
  const description = isRegister
    ? 'Start with a private account so every scope check belongs only to you.'
    : 'Sign in to your protected Scope Creep Guard workspace.'
  const endpoint = isRegister ? '/api/auth/register' : '/api/auth/login'

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')

    if (!email.trim()) {
      setError('Email is required.')
      return
    }
    if (!password) {
      setError('Password is required.')
      return
    }

    setIsSubmitting(true)
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      })

      if (!response.ok) {
        setError(await readErrorMessage(response))
        return
      }

      router.replace('/')
      router.refresh()
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'auth_submit_failed',
          mode,
          message: error instanceof Error ? error.message : 'Unknown auth error',
        }),
      )
      setError('Unable to reach the auth service. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="min-h-screen overflow-hidden bg-background text-foreground">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_20%_20%,oklch(0.93_0.03_158),transparent_34%),radial-gradient(circle_at_80%_0%,oklch(0.92_0.02_250),transparent_30%),linear-gradient(135deg,oklch(0.99_0.002_250),oklch(0.96_0.006_250))]" />
      <div className="absolute inset-x-0 top-0 -z-10 h-px bg-gradient-to-r from-transparent via-border to-transparent" />

      <div className="mx-auto grid min-h-screen max-w-6xl items-center gap-10 px-4 py-10 sm:px-6 lg:grid-cols-[1fr_26rem]">
        <section className="max-w-2xl">
          <span className="inline-flex items-center gap-2 rounded-lg border border-border bg-card/70 px-3 py-1.5 text-xs font-medium text-muted-foreground shadow-sm">
            <ShieldCheck className="size-4 text-foreground" aria-hidden="true" />
            Scope Creep Guard
          </span>
          <h1 className="mt-6 text-4xl font-semibold tracking-tight text-foreground text-balance sm:text-6xl">
            Keep client scope private, then check requests with confidence.
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-muted-foreground text-pretty">
            Email/password auth keeps every project, scope, and check history tied
            to the person who created it.
          </p>
        </section>

        <section className="rounded-2xl border border-border bg-card/85 p-6 shadow-sm backdrop-blur">
          <div>
            <h2 className="text-xl font-semibold text-foreground">{title}</h2>
            <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
              {description}
            </p>
          </div>

          <form onSubmit={submit} className="mt-6 flex flex-col gap-4">
            <div>
              <label
                htmlFor="auth-email"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                Email
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
                  placeholder="you@example.com"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="auth-password"
                className="mb-1.5 block text-sm font-medium text-foreground"
              >
                Password
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
                  placeholder="At least 8 characters"
                />
              </div>
            </div>

            {error && (
              <p className="rounded-lg bg-outscope-soft px-3 py-2 text-sm text-outscope-text">
                {error}
              </p>
            )}

            <Button type="submit" className="h-10 w-full" disabled={isSubmitting}>
              {isSubmitting
                ? isRegister
                  ? 'Creating account...'
                  : 'Signing in...'
                : isRegister
                  ? 'Create account'
                  : 'Sign in'}
            </Button>
          </form>

          <p className="mt-5 text-center text-sm text-muted-foreground">
            {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
            <Link
              href={isRegister ? '/login' : '/register'}
              className="font-medium text-foreground underline-offset-4 hover:underline"
            >
              {isRegister ? 'Sign in' : 'Create one'}
            </Link>
          </p>
        </section>
      </div>
    </main>
  )
}
