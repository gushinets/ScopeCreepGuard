import { createServer } from 'node:http'
import { afterEach, expect, it, vi } from 'vitest'

vi.mock('server-only', () => ({}))
vi.mock('@/lib/db', () => { throw new Error('Migrated project handlers must not import TypeScript persistence') })
afterEach(() => vi.unstubAllEnvs())

it('forwards exactly the five project methods while preserving response status and headers', async () => {
  const calls: string[] = []
  const server = createServer((request, response) => {
    calls.push(`${request.method} ${request.url}`)
    expect(request.headers.cookie).toBe('scg_session=synthetic')
    response.writeHead(404, { 'content-type': 'application/json', 'x-request-id': 'project-test' })
    response.end('{"error":"errors.projectNotFound"}')
  })
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve))
  vi.stubEnv('SCOPE_GUARD_API_ORIGIN', `http://127.0.0.1:${(server.address() as { port: number }).port}`)
  try {
    const collection = await import('@/app/api/projects/route')
    const detail = await import('@/app/api/projects/[id]/route')
    for (const [method, handler, path] of [
      ['GET', collection.GET, '/api/projects'], ['POST', collection.POST, '/api/projects'],
      ['GET', detail.GET, '/api/projects/owned-id'], ['PATCH', detail.PATCH, '/api/projects/owned-id'],
      ['DELETE', detail.DELETE, '/api/projects/owned-id'],
    ] as const) {
      const response = await handler(new Request(`http://frontend.test${path}`, {
        method, headers: { cookie: 'scg_session=synthetic' },
      }), { params: Promise.resolve({ id: 'owned-id' }) })
      expect(response.status).toBe(404)
      expect(await response.json()).toEqual({ error: 'errors.projectNotFound' })
      expect(response.headers.get('x-request-id')).toBe('project-test')
    }
    expect(calls).toEqual(['GET /api/projects', 'POST /api/projects', 'GET /api/projects/owned-id', 'PATCH /api/projects/owned-id', 'DELETE /api/projects/owned-id'])
  } finally {
    server.closeAllConnections()
    await new Promise<void>(resolve => server.close(() => resolve()))
  }
})
