import { createServer, type RequestListener } from 'node:http'
import type { AddressInfo } from 'node:net'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { forwardToBackend } from './forward'

vi.mock('server-only', () => ({}))

const servers: ReturnType<typeof createServer>[] = []
afterEach(async () => {
  vi.unstubAllEnvs()
  await Promise.all(servers.map((server) => new Promise<void>((resolve) => {
    server.closeAllConnections()
    server.close(() => resolve())
  })))
  servers.length = 0
})

async function backend(handler: RequestListener) {
  const server = createServer(handler)
  servers.push(server)
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve))
  return `http://127.0.0.1:${(server.address() as AddressInfo).port}`
}

describe('one-owner backend transport', () => {
  it('forwards exact method/query/body/cookies and preserves response plus separate cookies', async () => {
    let calls = 0
    const origin = await backend(async (request, response) => {
      calls += 1
      let body = ''
      for await (const chunk of request) body += chunk
      expect(request.method).toBe('POST')
      expect(request.url).toBe('/api/drafts?preview=1')
      expect(request.headers.cookie).toBe('scg_session=synthetic; locale=ru')
      expect(request.headers.origin).toBe('https://app.test')
      expect(request.headers.authorization).toBeUndefined()
      expect(request.headers['x-forwarded-host']).toBeUndefined()
      expect(body).toBe('{ "draftDocument": {"text":"Русский"} }')
      response.writeHead(201, {
        'Content-Type': 'application/json', 'Cache-Control': 'private, no-store',
        'Set-Cookie': ['scg_session=synthetic; HttpOnly; Path=/; SameSite=Lax',
          'locale=ru; Expires=Wed, 21 Oct 2026 07:28:00 GMT; Path=/'],
      })
      response.end('{"draft":{"id":"saved"}}')
    })
    vi.stubEnv('SCOPE_GUARD_API_ORIGIN', origin)
    const response = await forwardToBackend(new Request('https://app.test/api/drafts?preview=1', {
      method: 'POST', headers: { cookie: 'scg_session=synthetic; locale=ru', origin: 'https://app.test',
        'content-type': 'application/json', authorization: 'untrusted', 'x-forwarded-host': 'evil.test' },
      body: '{ "draftDocument": {"text":"Русский"} }',
    }))
    expect(response.status).toBe(201)
    expect(await response.text()).toBe('{"draft":{"id":"saved"}}')
    expect(response.headers.get('cache-control')).toBe('private, no-store')
    expect(response.headers.getSetCookie()).toHaveLength(2)
    expect(calls).toBe(1)
  })

  it('does not retry or reinterpret an upstream business failure', async () => {
    let calls = 0
    const origin = await backend((_request, response) => {
      calls += 1
      response.writeHead(429, { 'Content-Type': 'application/json' })
      response.end('{"error":"errors.analysisRateLimited"}')
    })
    vi.stubEnv('SCOPE_GUARD_API_ORIGIN', origin)
    const response = await forwardToBackend(new Request('https://app.test/api/analyze', {
      method: 'POST', body: '{}',
    }))
    expect(response.status).toBe(429)
    expect(await response.json()).toEqual({ error: 'errors.analysisRateLimited' })
    expect(calls).toBe(1)
  })

  it('preserves export and rate-limit headers without trusting caller routing headers', async () => {
    const origin = await backend((request, response) => {
      expect(request.headers.host).toBe(new URL(origin).host)
      expect(request.headers['x-forwarded-proto']).toBeUndefined()
      response.writeHead(200, {
        'Content-Type': 'application/x-ndjson; charset=utf-8',
        'Content-Disposition': 'attachment; filename="scope-creep-evaluations.jsonl"',
        'Cache-Control': 'private, no-store', 'Retry-After': '30', 'X-Request-ID': 'synthetic-id',
      })
      response.end('{"request":"Русский"}\n')
    })
    vi.stubEnv('SCOPE_GUARD_API_ORIGIN', origin)
    const response = await forwardToBackend(new Request('https://app.test/api/evaluations/export', {
      headers: { host: 'evil.test', 'x-forwarded-proto': 'http' },
    }))
    expect(response.headers.get('content-type')).toBe('application/x-ndjson; charset=utf-8')
    expect(response.headers.get('content-disposition')).toBe('attachment; filename="scope-creep-evaluations.jsonl"')
    expect(response.headers.get('retry-after')).toBe('30')
    expect(response.headers.get('x-request-id')).toBe('synthetic-id')
    expect(await response.text()).toBe('{"request":"Русский"}\n')
  })

  it('returns one transport failure without retrying a disconnected backend', async () => {
    let calls = 0
    const origin = await backend((request) => {
      calls += 1
      request.socket.destroy()
    })
    vi.stubEnv('SCOPE_GUARD_API_ORIGIN', origin)
    const response = await forwardToBackend(new Request('https://app.test/api/analyze', {
      method: 'POST', body: '{}',
    }))
    expect(response.status).toBe(503)
    expect(await response.json()).toEqual({ error: 'errors.requestFailed' })
    expect(calls).toBe(1)
  })

  it.each(['https://evil.test/api/auth/me', '//evil.test/api/auth/me', '/outside'])('cannot select a different upstream with %s', async (path) => {
    vi.stubEnv('SCOPE_GUARD_API_ORIGIN', 'http://127.0.0.1:9')
    const response = await forwardToBackend(new Request('https://app.test/api/auth/me'), path)
    expect(response.status).toBe(503)
    expect(await response.json()).toEqual({ error: 'errors.requestFailed' })
  })

  it('does not follow backend redirects and thereby resend credentials', async () => {
    let calls = 0
    const origin = await backend((_request, response) => {
      calls += 1
      response.writeHead(307, { Location: 'https://evil.test/' })
      response.end()
    })
    vi.stubEnv('SCOPE_GUARD_API_ORIGIN', origin)
    const response = await forwardToBackend(new Request('https://app.test/api/auth/me'))
    expect(response.status).toBe(307)
    expect(calls).toBe(1)
  })
})
