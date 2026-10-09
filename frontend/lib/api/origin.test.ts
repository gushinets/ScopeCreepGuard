vi.mock('server-only', () => ({}))
import { afterEach, expect, it, vi } from 'vitest'
import { NextRequest } from 'next/server'
import { proxy as middleware } from '@/proxy'

afterEach(() => vi.unstubAllEnvs())

it.each(['/api/auth/register', '/api/locale', '/api/analyze'])('rejects a foreign Origin before auth or body at %s', async (path) => {
  vi.stubEnv('SCOPE_GUARD_ALLOWED_ORIGINS', '["https://app.test"]')
  const response = await middleware(new NextRequest(`https://app.test${path}`, {
    method: 'POST', headers: { origin: 'https://evil.test' },
  }))
  expect(response.status).toBe(403)
  expect(await response.json()).toEqual({ error: 'errors.requestFailed' })
})

it('allows configured origins and originless server clients on public routes', async () => {
  vi.stubEnv('SCOPE_GUARD_ALLOWED_ORIGINS', '["https://app.test"]')
  for (const headers of [new Headers(), new Headers({ origin: 'https://app.test' })]) {
    const response = await middleware(new NextRequest('https://app.test/api/locale', { method: 'POST', headers }))
    expect(response.headers.get('x-middleware-next')).toBe('1')
  }
})

it.each(['null', 'https://app.test.evil.test', 'https://app.test:444', 'https://app.test/'])('requires an exact configured origin for %s', async (origin) => {
  vi.stubEnv('SCOPE_GUARD_ALLOWED_ORIGINS', '["https://app.test"]')
  const response = await middleware(new NextRequest('https://app.test/api/locale', { method: 'POST', headers: { origin } }))
  expect(response.status).toBe(403)
})
