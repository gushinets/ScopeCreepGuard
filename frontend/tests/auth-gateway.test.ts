import { createServer } from 'node:http'
import { afterEach, expect, it, vi } from 'vitest'

vi.mock('server-only', () => ({}))
vi.mock('@/lib/db', () => { throw new Error('Migrated authentication must not import the TypeScript database') })

afterEach(() => vi.unstubAllEnvs())

it('forwards all four auth handlers, cookies and errors exactly once to the configured origin', async () => {
  const calls: string[] = []
  const server = createServer((request, response) => {
    calls.push(`${request.method} ${request.url}`)
    expect(request.headers.cookie).toBe('scg_session=synthetic')
    response.writeHead(401, { 'content-type': 'application/json', 'set-cookie': 'scg_session=; Path=/; Max-Age=0; HttpOnly; SameSite=lax' })
    response.end('{"error":"errors.authRequired"}')
  })
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve))
  const address = server.address() as { port: number }
  vi.stubEnv('SCOPE_GUARD_API_ORIGIN', `http://127.0.0.1:${address.port}`)
  try {
    const handlers = [
      ['register', (await import('@/app/api/auth/register/route')).POST],
      ['login', (await import('@/app/api/auth/login/route')).POST],
      ['logout', (await import('@/app/api/auth/logout/route')).POST],
      ['me', (await import('@/app/api/auth/me/route')).GET],
    ] as const
    for (const [name, handler] of handlers) {
      const response = await handler(new Request(`http://frontend.test/api/auth/${name}`, {
        method: name === 'me' ? 'GET' : 'POST', headers: { cookie: 'scg_session=synthetic' },
      }))
      expect(response.status).toBe(401)
      expect(await response.json()).toEqual({ error: 'errors.authRequired' })
      expect(response.headers.get('set-cookie')).toContain('Max-Age=0')
    }
    expect(calls).toEqual(['POST /api/auth/register', 'POST /api/auth/login', 'POST /api/auth/logout', 'GET /api/auth/me'])
  } finally {
    server.closeAllConnections()
    await new Promise<void>(resolve => server.close(() => resolve()))
  }
})
