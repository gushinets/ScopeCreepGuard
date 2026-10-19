import { afterEach, expect, it, vi } from 'vitest'
import { apiFetch, apiJson, ApiClientError } from '@/shared/api/client'

afterEach(() => vi.unstubAllGlobals())

it('retains workflow fields, terminal identity and retry/correlation headers', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({
    error: 'errors.draftConflict', fields: { currency: 'required' }, operationId: 'saved-operation',
  }, { status: 409, headers: { 'Retry-After': '30', 'X-Request-ID': 'request-one' } })))
  try { await apiJson('/api/v2/drafts/test') } catch (error) {
    expect(error).toMatchObject({ status: 409, terminal: true, fields: { currency: 'required' } })
    expect((error as ApiClientError & { headers: Headers }).headers.get('retry-after')).toBe('30')
    expect((error as ApiClientError & { headers: Headers }).headers.get('x-request-id')).toBe('request-one')
    return
  }
  throw new Error('Expected structured API failure')
})

it('keeps same-origin credentials and does one request without retrying errors', async () => {
  const fetcher = vi.fn().mockResolvedValue(Response.json({ error: 'errors.authRequired' }, { status: 401 }))
  vi.stubGlobal('fetch', fetcher)
  await expect(apiJson('/api/projects')).rejects.toMatchObject({ code: 'errors.authRequired', status: 401 })
  expect(fetcher).toHaveBeenCalledTimes(1)
  expect(fetcher.mock.calls[0][1]).toMatchObject({ credentials: 'same-origin' })
})

it('preserves successful JSON and export headers/body', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(Response.json({ ok: true }))
    .mockResolvedValueOnce(new Response('{}\n', { headers: { 'content-type': 'application/x-ndjson' } })))
  expect(await apiJson('/api/locale')).toEqual({ ok: true })
  const response = await apiFetch('/api/evaluations/export')
  expect(response.headers.get('content-type')).toBe('application/x-ndjson')
  expect(await response.text()).toBe('{}\n')
})

it.each(['<html>gateway error</html>', JSON.stringify({ error: 'private detail' })])('maps malformed/unknown failures safely: %s', async (body) => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 502 })))
  await expect(apiJson('/api/projects')).rejects.toMatchObject({ code: 'errors.requestFailed', status: 502 })
})

it('propagates cancellation instead of retrying and rejects off-origin paths', async () => {
  const error = new DOMException('aborted', 'AbortError')
  const fetcher = vi.fn().mockRejectedValue(error)
  vi.stubGlobal('fetch', fetcher)
  await expect(apiJson('/api/projects')).rejects.toBe(error)
  await expect(apiJson('https://foreign.test/api/projects')).rejects.toBeInstanceOf(ApiClientError)
  expect(fetcher).toHaveBeenCalledTimes(1)
})
