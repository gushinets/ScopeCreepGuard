// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { IntlProvider } from 'use-intl'
import { MemoryRouter, useLocation } from 'react-router'
import en from '@/shared/i18n/messages/en.json'
import { MyDraftsView } from './my-drafts-view'

const { store } = vi.hoisted(() => ({ store: { listDrafts: vi.fn(), openDraft: vi.fn(), draftError: '', draftProjects: [{ id: '11111111-1111-4111-8111-111111111111', name: 'Project One' }] } }))
vi.mock('./context', () => ({ useDrafts: () => store }))
const item = { id: 'd1', projectId: '11111111-1111-4111-8111-111111111111', projectName: 'Project One', requestPreview: 'Saved request', verdict: null, createdAt: '2026-10-20T01:02:03Z', updatedAt: '2026-10-21T04:05:06Z' }
const result = { drafts: [item], total: 1, hasDrafts: true }
function Location() { return <output aria-label="Location">{useLocation().search}</output> }
function show(path = '/drafts?keep=yes') {
  return render(<IntlProvider locale="en" messages={en}><MemoryRouter initialEntries={[path]}><MyDraftsView /><Location /></MemoryRouter></IntlProvider>)
}
beforeEach(() => { store.listDrafts.mockReset().mockResolvedValue(result); store.openDraft.mockReset() })
afterEach(cleanup)

it('shows explicit UTC creation and modification times, plus Filter and Export', async () => {
  show()
  expect(await screen.findByText('Saved request')).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Filter' })).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Export' })).toBeTruthy()
  expect(screen.getByText(/Created \(UTC\)/).textContent).toContain('01:02:03')
  expect(screen.getByText(/Modified \(UTC\)/).textContent).toContain('04:05:06')
  expect(store.listDrafts.mock.calls[0][1]).toEqual({ limit: 50, offset: 0 })
})

it('applies combined filters in the URL and resets without losing other parameters', async () => {
  show()
  await screen.findByText('Saved request')
  fireEvent.click(screen.getByRole('button', { name: 'Filter' }))
  fireEvent.change(await screen.findByLabelText('Project'), { target: { value: '11111111-1111-4111-8111-111111111111' } })
  fireEvent.change(screen.getByLabelText('Created from (UTC)'), { target: { value: '2026-10-20' } })
  fireEvent.change(screen.getByLabelText('Created to (UTC)'), { target: { value: '2026-10-21' } })
  fireEvent.change(screen.getByLabelText('Creation order'), { target: { value: 'oldest' } })
  store.listDrafts.mockResolvedValue({ drafts: [], total: 0, hasDrafts: true })
  fireEvent.click(screen.getByRole('button', { name: 'Apply filters' }))
  await waitFor(() => expect(screen.getByLabelText('Location').textContent).toContain('draftProject=11111111-1111-4111-8111-111111111111'))
  expect(screen.getByLabelText('Location').textContent).toContain('keep=yes')
  expect(store.listDrafts.mock.calls.at(-1)?.[0]).toEqual({ projectId: '11111111-1111-4111-8111-111111111111', createdFrom: '2026-10-20', createdTo: '2026-10-21', sort: 'oldest' })
  expect(await screen.findByText('No Drafts match these filters')).toBeTruthy()
  store.listDrafts.mockResolvedValue(result)
  fireEvent.click(screen.getByRole('button', { name: 'Filter' }))
  fireEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Clear filters' }))
  await waitFor(() => expect(screen.getByLabelText('Location').textContent).toBe('?keep=yes'))
  expect(await screen.findByText('Saved request')).toBeTruthy()
})

it('ignores an older response after filters change and exports all matches', async () => {
  let finish!: (value: typeof result) => void
  store.listDrafts.mockReturnValueOnce(new Promise(resolve => { finish = resolve })).mockResolvedValue(result)
  const fetcher = vi.fn().mockResolvedValue(new Response('csv', { headers: { 'Content-Disposition': 'attachment; filename="drafts-en.csv"' } }))
  vi.stubGlobal('fetch', fetcher)
  URL.createObjectURL = vi.fn(() => 'blob:test'); URL.revokeObjectURL = vi.fn()
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  show()
  fireEvent.click(screen.getByRole('button', { name: 'Filter' }))
  fireEvent.change(await screen.findByLabelText('Creation order'), { target: { value: 'oldest' } })
  fireEvent.click(screen.getByRole('button', { name: 'Apply filters' }))
  await screen.findByText('Saved request')
  await act(async () => finish({ ...result, drafts: [{ ...item, requestPreview: 'Obsolete' }] }))
  expect(screen.queryByText('Obsolete')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Export' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Download CSV' }))
  await waitFor(() => expect(fetcher).toHaveBeenCalled())
  expect(String(fetcher.mock.calls[0][0])).toBe('/api/v2/drafts/export.csv?sort=oldest&locale=en')
  await waitFor(() => expect(click).toHaveBeenCalled())
  click.mockRestore(); vi.unstubAllGlobals()
})

it('rejects malformed filter links instead of loading every Draft', async () => {
  show('/drafts?draftProject=not-a-uuid')
  expect(await screen.findByRole('alert')).toBeTruthy()
  expect(store.listDrafts).not.toHaveBeenCalled()
})

it('distinguishes an empty account from a failed load and retries', async () => {
  store.listDrafts.mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ drafts: [], total: 0, hasDrafts: false })
  show()
  expect(await screen.findByRole('alert')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByText('No drafts yet')).toBeTruthy()
  expect(screen.queryByText('No Drafts match these filters')).toBeNull()
})

it('uses pages of 50 and recovers an empty page after archiving', async () => {
  store.listDrafts.mockResolvedValueOnce({ ...result, total: 51 }).mockResolvedValueOnce({ drafts: [], total: 50, hasDrafts: true }).mockResolvedValue(result)
  show()
  fireEvent.click(await screen.findByRole('button', { name: 'Next' }))
  await waitFor(() => expect(store.listDrafts.mock.calls.some(call => call[1].offset === 50)).toBe(true))
  await waitFor(() => expect(store.listDrafts.mock.calls.at(-1)?.[1].offset).toBe(0))
  expect(await screen.findByText('Saved request')).toBeTruthy()
})

it.each(['draftCreatedFrom=2026-13-40', 'draftCreatedFrom=2026-10-21&draftCreatedTo=2026-10-20', 'draftSort=unknown', 'draftPage=-1'])('shows a safe reset for invalid filter URL %s', async query => {
  show('/drafts?' + query)
  expect(await screen.findByRole('alert')).toBeTruthy()
  expect(store.listDrafts).not.toHaveBeenCalled()
})
