import { afterEach, expect, it, vi } from 'vitest'

const forwarding = vi.hoisted(() => ({ call: vi.fn() }))
vi.mock('@/lib/api/forward', () => ({ forwardToBackend: forwarding.call }))

afterEach(() => {
  forwarding.call.mockReset()
  vi.unstubAllEnvs()
})

it('forwards history, evaluation, export and locale exactly once', async () => {
  const routes = [
    ['POST', '/api/projects/project-id/history', (await import('@/app/api/projects/[id]/history/route')).POST, { params: Promise.resolve({ id: 'project-id' }) }],
    ['POST', '/api/evaluations', (await import('@/app/api/evaluations/route')).POST, undefined],
    ['GET', '/api/evaluations/export', (await import('@/app/api/evaluations/export/route')).GET, undefined],
    ['POST', '/api/locale', (await import('@/app/api/locale/route')).POST, undefined],
  ] as const
  for (const [method, path, handler, context] of routes) {
    forwarding.call.mockClear()
    const request = new Request(`https://frontend.test${path}`, {
      method,
      headers: { cookie: 'scg_session=synthetic; locale=ru', origin: 'https://frontend.test' },
      ...(method === 'GET' ? {} : { body: '{ "value": "😀 Ж" }' }),
    })
    const response = new Response('raw', { status: 409, headers: { 'x-request-id': 'remaining' } })
    forwarding.call.mockResolvedValue(response)
    expect(await handler(request, context as never)).toBe(response)
    expect(forwarding.call).toHaveBeenCalledExactlyOnceWith(request, path)
  }
})

it('returns the established outage response without a TypeScript fallback', async () => {
  forwarding.call.mockImplementation(async () =>
    Response.json({ error: 'errors.requestFailed' }, { status: 503 }),
  )
  const routes = [
    ['POST', '/api/projects/project-id/history', (await import('@/app/api/projects/[id]/history/route')).POST, { params: Promise.resolve({ id: 'project-id' }) }],
    ['POST', '/api/evaluations', (await import('@/app/api/evaluations/route')).POST, undefined],
    ['GET', '/api/evaluations/export', (await import('@/app/api/evaluations/export/route')).GET, undefined],
    ['POST', '/api/locale', (await import('@/app/api/locale/route')).POST, undefined],
  ] as const
  for (const [method, path, handler, context] of routes) {
    const response = await handler(new Request(`https://frontend.test${path}`, { method }), context as never)
    expect(response.status).toBe(503)
    expect(await response.json()).toEqual({ error: 'errors.requestFailed' })
  }
  expect(forwarding.call).toHaveBeenCalledTimes(4)
})
