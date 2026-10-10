import { afterEach, expect, it, vi } from 'vitest'

const forwarding = vi.hoisted(() => ({ call: vi.fn() }))
vi.mock('@/lib/api/forward', () => ({ forwardToBackend: forwarding.call }))

afterEach(() => vi.clearAllMocks())

it('forwards each generation operation once, preserving the original request and response', async () => {
  const routes = [
    ['/api/analyze', await import('@/app/api/analyze/route')],
    ['/api/replies/regenerate', await import('@/app/api/replies/regenerate/route')],
    ['/api/client-materials/language', await import('@/app/api/client-materials/language/route')],
    ['/api/change-orders/estimate', await import('@/app/api/change-orders/estimate/route')],
  ] as const
  for (const [path, route] of routes) {
    forwarding.call.mockClear()
    const request = new Request(`https://example.test${path}?correlation=value`, { method: 'POST', headers: { cookie: 'synthetic', origin: 'https://example.test' }, body: '{"request":" 😀 "}' })
    const response = new Response('{"error":"errors.analysisFailed"}', { status: 502, headers: { 'x-request-id': 'synthetic' } })
    forwarding.call.mockResolvedValue(response)
    expect(await route.POST(request)).toBe(response)
    expect(forwarding.call).toHaveBeenCalledExactlyOnceWith(request, path)
  }
})
