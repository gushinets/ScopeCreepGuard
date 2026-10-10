import { createServer } from 'node:http'
import { afterEach, expect, it, vi } from 'vitest'

vi.mock('server-only', () => ({}))
vi.mock('@/lib/db', () => { throw new Error('Draft gateway must not import TS persistence') })
afterEach(() => vi.unstubAllEnvs())

it('forwards all four draft methods once with raw body and private read headers', async () => {
  const calls: string[] = []
  const server = createServer(async (request, response) => {
    calls.push(`${request.method} ${request.url}`)
    expect(request.headers.cookie).toBe('scg_session=synthetic')
    expect(request.headers.origin).toBe('https://frontend.test')
    let body = ''
    for await (const chunk of request) body += chunk
    if (request.method !== 'GET') expect(body).toBe('{ "draftDocument": {"text":"😀 Ж"} }')
    response.writeHead(404, { 'content-type': 'application/json', 'x-request-id': 'draft-test' })
    response.end('{"error":"errors.draftNotFound"}')
  })
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve))
  vi.stubEnv('SCOPE_GUARD_API_ORIGIN', `http://127.0.0.1:${(server.address() as { port: number }).port}`)
  try {
    const collection = await import('@/app/api/drafts/route')
    const detail = await import('@/app/api/drafts/[id]/route')
    for (const [method, handler, path] of [
      ['GET', collection.GET, '/api/drafts'], ['POST', collection.POST, '/api/drafts'],
      ['GET', detail.GET, '/api/drafts/owned-id'], ['PUT', detail.PUT, '/api/drafts/owned-id'],
    ] as const) {
      const response = await handler(new Request(`https://frontend.test${path}`, {
        method, headers: { cookie: 'scg_session=synthetic', origin: 'https://frontend.test' },
        ...(method === 'GET' ? {} : { body: '{ "draftDocument": {"text":"😀 Ж"} }' }),
      }), { params: Promise.resolve({ id: 'owned-id' }) })
      expect(response.status).toBe(404)
      expect(await response.json()).toEqual({ error: 'errors.draftNotFound' })
      expect(response.headers.get('x-request-id')).toBe('draft-test')
      if (method === 'GET') expect(response.headers.get('cache-control')).toBe('private, no-store')
    }
    expect(calls).toEqual(['GET /api/drafts', 'POST /api/drafts', 'GET /api/drafts/owned-id', 'PUT /api/drafts/owned-id'])
  } finally {
    server.closeAllConnections()
    await new Promise<void>(resolve => server.close(() => resolve()))
  }
})

it('returns established outage error without fallback and keeps GET responses private', async () => {
  vi.stubEnv('SCOPE_GUARD_API_ORIGIN', '')
  const collection = await import('@/app/api/drafts/route')
  const detail = await import('@/app/api/drafts/[id]/route')
  for (const [method, handler, path] of [
    ['GET', collection.GET, '/api/drafts'], ['POST', collection.POST, '/api/drafts'],
    ['GET', detail.GET, '/api/drafts/x'], ['PUT', detail.PUT, '/api/drafts/x'],
  ] as const) {
    const response = await handler(new Request(`https://frontend.test${path}`, { method }), { params: Promise.resolve({ id: 'x' }) })
    expect(response.status).toBe(503)
    expect(await response.json()).toEqual({ error: 'errors.requestFailed' })
    if (method === 'GET') expect(response.headers.get('cache-control')).toBe('private, no-store')
  }
})
