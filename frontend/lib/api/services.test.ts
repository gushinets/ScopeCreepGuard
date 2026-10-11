import { afterEach, expect, it, vi } from 'vitest'
import { downloadChangeOrder, extractScope } from './services'

afterEach(() => vi.unstubAllGlobals())

it('exports saved unchanged data through GET and edits through POST without saving', async () => {
  const request = vi.fn().mockImplementation(async () => new Response('%PDF-', { headers: { 'Content-Type': 'application/pdf', 'Content-Disposition': 'attachment; filename="change-order-safe.pdf"' } }))
  vi.stubGlobal('fetch', request)
  const draft = { description: 'My edit' } as Parameters<typeof downloadChangeOrder>[0]['draft']
  await downloadChangeOrder({ draft, projectId: 'project', draftId: 'saved', savedUnchanged: true })
  expect(request.mock.calls[0][0]).toBe('/api/drafts/saved/pdf')
  await downloadChangeOrder({ draft, projectId: 'project', draftId: 'saved', savedUnchanged: false })
  expect(request.mock.calls[1][0]).toBe('/api/change-orders/pdf')
  expect(JSON.parse(request.mock.calls[1][1].body)).toEqual({ projectId: 'project', draftId: 'saved', changeOrder: draft })
})

it('uploads one file without manually setting multipart content type', async () => {
  const request = vi.fn().mockResolvedValue(Response.json({ text: 'Scope', warnings: [] }))
  vi.stubGlobal('fetch', request)
  const result = await extractScope(new File(['Scope'], 'scope.md'))
  expect(result.text).toBe('Scope')
  expect(request.mock.calls[0][0]).toBe('/api/scope/extract')
  expect(request.mock.calls[0][1].body).toBeInstanceOf(FormData)
  expect(request.mock.calls[0][1].headers).toBeUndefined()
})
