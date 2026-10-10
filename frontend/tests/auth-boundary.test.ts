import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { NextRequest } from 'next/server'
import { SignJWT } from 'jose'
import { proxy as middleware } from '@/proxy'
import { SESSION_COOKIE_NAME } from '@/lib/auth/session'
import { createSessionToken } from '@/tests/session-fixture'
import { POST as logout } from '@/app/api/auth/logout/route'
import { ERROR_CODES } from '@/lib/api/errors'
import { createServer, type Server } from 'node:http'

vi.mock('server-only', () => ({}))
let server: Server
let ownerStatus = 200

const secret = 'migration-smoke-secret-at-least-32-characters'

function request(path: string, token?: string) {
  return new NextRequest(`http://localhost:3000${path}`, {
    headers: token ? { cookie: `${SESSION_COOKIE_NAME}=${token}` } : {},
  })
}

describe('relocated Next.js authentication boundary', () => {
  beforeEach(async () => {
    vi.stubEnv('AUTH_SECRET', secret)
    ownerStatus = 200
    server = createServer((incoming, response) => {
      expect(incoming.headers.cookie).toContain('scg_session=')
      if (incoming.url === '/api/auth/logout') {
        response.writeHead(200, { 'content-type': 'application/json', 'set-cookie': 'scg_session=; Path=/; Max-Age=0; HttpOnly; SameSite=lax' })
        response.end('{"ok":true}')
      } else {
        response.writeHead(ownerStatus, { 'content-type': 'application/json', ...(ownerStatus === 401 ? { 'set-cookie': 'scg_session=; Path=/; Max-Age=0; HttpOnly; SameSite=lax' } : {}) })
        response.end(ownerStatus === 200 ? '{"user":{"id":"migration-user","email":"user@example.test"}}' : '{"error":"errors.authRequired"}')
      }
    })
    await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve))
    vi.stubEnv('SCOPE_GUARD_API_ORIGIN', `http://127.0.0.1:${(server.address() as { port: number }).port}`)
  })
  afterEach(async () => {
    server.closeAllConnections()
    await new Promise<void>(resolve => server.close(() => resolve()))
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
    const response = await logout(new Request('http://localhost:3000/api/auth/logout', { method: 'POST', headers: { cookie: 'scg_session=synthetic' } }))
    expect(response.headers.get('set-cookie')).toBe('scg_session=; Path=/; Max-Age=0; HttpOnly; SameSite=lax')
  })

  it.each([401, 500, 503])('allows login recovery when Python owner lookup returns %s', async status => {
    ownerStatus = status
    const token = await createSessionToken({ id: 'migration-user', email: 'user@example.test' })
    const response = await middleware(request('/login', token))
    expect(response.headers.get('x-middleware-next')).toBe('1')
    expect(response.headers.get('location')).toBeNull()
    expect(response.headers.get('set-cookie')?.includes('Max-Age=0') ?? false).toBe(status === 401)
  })
})
