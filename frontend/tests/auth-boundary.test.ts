import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { NextRequest } from 'next/server'
import { SignJWT } from 'jose'
import { middleware } from '@/middleware'
import { createSessionToken, SESSION_COOKIE_NAME } from '@/lib/auth/session'
import { POST as logout } from '@/app/api/auth/logout/route'
import { ERROR_CODES } from '@/lib/api/errors'

const secret = 'migration-smoke-secret-at-least-32-characters'

function request(path: string, token?: string) {
  return new NextRequest(`http://localhost:3000${path}`, {
    headers: token ? { cookie: `${SESSION_COOKIE_NAME}=${token}` } : {},
  })
}

describe('relocated Next.js authentication boundary', () => {
  beforeEach(() => vi.stubEnv('AUTH_SECRET', secret))
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.restoreAllMocks()
  })

  it('rewrites the unauthenticated home page to login', async () => {
    const response = await middleware(request('/'))
    expect(response.headers.get('x-middleware-rewrite')).toBe('http://localhost:3000/login')
  })

  it.each(['/login', '/register', '/api/auth/login', '/api/locale'])('keeps %s public', async path => {
    const response = await middleware(request(path))
    expect(response.headers.get('x-middleware-next')).toBe('1')
  })

  it('keeps business APIs protected in Next.js', async () => {
    const response = await middleware(request('/api/projects'))
    expect(response.status).toBe(401)
    expect(await response.json()).toEqual({ error: ERROR_CODES.authRequired })
  })

  it('accepts existing signed sessions and redirects authenticated login', async () => {
    const token = await createSessionToken({ id: 'migration-user', email: 'user@example.test' })
    expect((await middleware(request('/api/projects', token))).headers.get('x-middleware-next')).toBe('1')
    expect((await middleware(request('/login', token))).headers.get('location')).toBe('http://localhost:3000/')
  })

  it('rejects an expired signed session', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const token = await new SignJWT({ email: 'user@example.test' })
      .setProtectedHeader({ alg: 'HS256' }).setSubject('migration-user')
      .setExpirationTime(1).sign(new TextEncoder().encode(secret))
    expect((await middleware(request('/api/projects', token))).status).toBe(401)
  })

  it('logout expires the existing session cookie', async () => {
    const response = await logout()
    const cookie = response.cookies.get(SESSION_COOKIE_NAME)
    expect(cookie?.value).toBe('')
    expect(cookie?.maxAge).toBe(0)
    expect(cookie?.path).toBe('/')
    expect(cookie?.httpOnly).toBe(true)
  })
})
