import { afterEach, expect, it, vi } from 'vitest'
import { apiFetch, apiJson, ApiClientError } from './client'

afterEach(() => vi.unstubAllGlobals())

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
