// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { NextIntlClientProvider } from 'next-intl'
import en from '@/messages/en.json'
import ru from '@/messages/ru.json'
import { analysisFixture, documentFixture } from '@/lib/drafts/fixtures'
import { StoreProvider, useStore } from './store'
import { AppShell } from './app-shell'
import { ResultPanel } from './result-panel'
import { HistoryView } from './history-view'
import { MyDraftsView } from './my-drafts-view'
import type { Project } from '@/lib/types'

const navigation = vi.hoisted(() => ({ router: { replace: vi.fn() } }))
vi.mock('next/navigation', () => ({ useRouter: () => navigation.router }))
vi.mock('@/lib/change-order/pdf', () => ({ createChangeOrderPdf: vi.fn() }))
const project: Project = { id: 'p1', name: 'Website', industry: 'Development', scope: 'Build five pages. Additional pages are outside the agreed scope and cost extra.', startDate: '2026-01-01', pricingModel: 'hourly', currency: 'EUR', hourlyRate: '100', fixedPrice: null, history: [] }
const saved = { id: 'd1', projectId: 'p1', historyEntryId: 'h1', status: 'draft', createdAt: '2026-10-06T12:00:00.000Z', updatedAt: '2026-10-06T12:00:00.000Z', locale: 'en', requestLanguage: 'en', clientMaterialLanguage: 'en', analysisSnapshot: analysisFixture, draftDocument: documentFixture, request: 'Add another page' }
const fetchMock = vi.fn()
let savedDocument = documentFixture
let created = false

beforeEach(() => {
  localStorage.clear()
  window.history.replaceState({}, '', '/')
  savedDocument = structuredClone(documentFixture)
  created = false
  fetchMock.mockReset()
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    let body: unknown
    if (url === '/api/auth/me') body = { user: { id: 'u1', email: 'owner@example.test' } }
    else if (url === '/api/projects') body = { projects: [{ ...project, history: created ? [{ id: 'h1', draftId: 'd1', request: saved.request, date: '2026-10-06', verdict: 'out_of_scope', summary: 'Extra page' }] : [] }] }
    else if (url === '/api/analyze') body = { result: analysisFixture }
    else if (url === '/api/drafts' && init?.method === 'POST') {
      if (!created) savedDocument = JSON.parse(String(init.body)).draftDocument
      created = true
      body = { draft: { ...saved, draftDocument: savedDocument }, entry: { id: 'h1', draftId: 'd1', request: saved.request, date: '2026-10-06', verdict: 'out_of_scope', summary: 'Extra page' } }
    } else if (url === '/api/drafts') body = { drafts: created ? [{ id: 'd1', requestPreview: saved.request, projectName: 'Website', verdict: 'out_of_scope', createdAt: saved.createdAt, updatedAt: saved.updatedAt }] : [] }
    else if (url === '/api/drafts/d1' && init?.method === 'PUT') { savedDocument = JSON.parse(String(init.body)).draftDocument; body = { draft: { ...saved, draftDocument: savedDocument } } }
    else if (url === '/api/drafts/d1') body = { draft: { ...saved, draftDocument: savedDocument } }
    else if (url === '/api/change-orders/estimate') body = { result: analysisFixture }
    else throw new Error('Unexpected API: ' + url)
    return { ok: true, json: async () => body }
  })
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.clearAllMocks() })

function Workspace() {
  const store = useStore()
  return <><input aria-label="Request" value={store.requestText} onChange={(e) => store.setRequestText(e.target.value)} />
    <button disabled={!store.selectedProject} onClick={store.runCheck}>Run</button>
    <button onClick={() => store.setView('drafts')}>Drafts navigation</button>
    <button onClick={() => store.setView('history')}>History navigation</button>
    {store.view === 'drafts' ? <MyDraftsView /> : store.view === 'history' ? <HistoryView /> : <ResultPanel />}
  </>
}
function app(locale: 'en' | 'ru' = 'en') {
  return render(<NextIntlClientProvider locale={locale} messages={locale === 'ru' ? ru : en}><StoreProvider><Workspace /></StoreProvider></NextIntlClientProvider>)
}
async function analyze(locale: 'en' | 'ru' = 'en') {
  const view = app(locale)
  await waitFor(() => expect((screen.getByText('Run') as HTMLButtonElement).disabled).toBe(false))
  fireEvent.change(screen.getByLabelText('Request'), { target: { value: 'Add another page' } })
  fireEvent.click(screen.getByText('Run'))
  await screen.findByText('Why this verdict')
  return view
}

it('does not register history or create a draft after analysis alone', async () => {
  await analyze()
  expect(created).toBe(false)
  expect(fetchMock.mock.calls.some(([url]) => String(url).includes('/history'))).toBe(false)
  expect(fetchMock.mock.calls.some(([url, init]) => url === '/api/drafts' && init?.method === 'POST')).toBe(false)
  expect(screen.getByRole('button', { name: 'Create draft' })).toBeTruthy()
})

it('creates the complete current document and changes the action to Save without refreshing', async () => {
  await analyze()
  fireEvent.change(screen.getByLabelText('Editable reply to client'), { target: { value: 'My terms' } })
  fireEvent.click(screen.getByRole('button', { name: 'Create Change Order' }))
  await screen.findByText('Change order draft')
  fireEvent.change(document.querySelector('#co-description')!, { target: { value: 'My custom scope' } })
  fireEvent.change(document.querySelector('#co-additionalCost')!, { target: { value: '175' } })
  fireEvent.click(screen.getByRole('button', { name: 'Create draft' }))
  await screen.findByRole('button', { name: 'Save' })
  expect(savedDocument.reply.text).toBe('My terms')
  expect(savedDocument.changeOrder?.description).toBe('My custom scope')
  expect(savedDocument.changeOrder?.additionalCost).toBe('175')
  expect((screen.getByLabelText('Editable reply to client') as HTMLTextAreaElement).value).toBe('My terms')
  fireEvent.change(document.querySelector('#co-description')!, { target: { value: 'Updated scope' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  await waitFor(() => expect(savedDocument.changeOrder?.description).toBe('Updated scope'))
})

it('opens persisted drafts after reload with empty localStorage and ignores conflicting old edits', async () => {
  created = true
  localStorage.setItem('scg:change-order:u1:p1:h1', JSON.stringify({ ...documentFixture.changeOrder, description: 'Stale local edit' }))
  const view = app()
  await waitFor(() => expect((screen.getByText('Run') as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(screen.getByText('Drafts navigation'))
  await screen.findByText('My drafts')
  fireEvent.click(await screen.findByRole('button', { name: /Add another page/ }))
  await waitFor(() => expect((document.querySelector('#co-description') as HTMLTextAreaElement)?.value).toBe('My own scope'))
  expect((screen.getByLabelText('Editable reply to client') as HTMLTextAreaElement).value).toBe('My edited reply')
  view.unmount()
  localStorage.clear()
  app()
  await waitFor(() => expect((document.querySelector('#co-description') as HTMLTextAreaElement)?.value).toBe('My own scope'))
  expect(screen.getByText('Not included')).toBeTruthy()
})

it('renders legacy history safely without offering a nonexistent saved document', async () => {
  fetchMock.mockImplementation(async (url: string) => ({ ok: true, json: async () => url === '/api/auth/me' ? { user: { id: 'u1' } } : { projects: [{ ...project, history: [{ id: 'old', date: '2026-10-01', request: 'Legacy request', verdict: 'in_scope', summary: 'Included' }] }] } }))
  app()
  await waitFor(() => expect((screen.getByText('Run') as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(screen.getByText('History navigation'))
  await screen.findByText('Legacy request')
  expect(screen.queryByText('Open saved draft')).toBeNull()
})

it.each(['en', 'ru'] as const)('uses localized navigation, Create draft and Save actions in %s', async (locale) => {
  render(<NextIntlClientProvider locale={locale} messages={locale === 'ru' ? ru : en}><AppShell /></NextIntlClientProvider>)
  const draftNav = await screen.findByRole('button', { name: locale === 'ru' ? 'Мои черновики' : 'My drafts' })
  fireEvent.click(draftNav)
  await screen.findByText(locale === 'ru' ? 'Черновиков пока нет' : 'No drafts yet')
  fireEvent.click(screen.getByRole('button', { name: locale === 'ru' ? 'Проверка запроса' : 'Scope check' }))
  fireEvent.change(screen.getByLabelText(locale === 'ru' ? 'Новый запрос клиента' : 'New client request'), { target: { value: 'Add another page' } })
  fireEvent.click(screen.getByRole('button', { name: locale === 'ru' ? 'Проверить запрос' : 'Check scope' }))
  const create = await screen.findByRole('button', { name: locale === 'ru' ? 'Создать черновик' : 'Create draft' })
  fireEvent.click(create)
  await screen.findByRole('button', { name: locale === 'ru' ? 'Сохранить' : 'Save' })
})

it('disables creation while pending and ignores repeated clicks', async () => {
  await analyze()
  const normalFetch = fetchMock.getMockImplementation()!
  let finish!: () => void
  const pending = new Promise<void>((resolve) => { finish = resolve })
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    if (url === '/api/drafts' && init?.method === 'POST') await pending
    return normalFetch(url, init)
  })
  const create = screen.getByRole('button', { name: 'Create draft' })
  fireEvent.click(create)
  fireEvent.click(create)
  expect((screen.getByRole('button', { name: 'Creating draft…' }) as HTMLButtonElement).disabled).toBe(true)
  expect(fetchMock.mock.calls.filter(([url, init]) => url === '/api/drafts' && init?.method === 'POST')).toHaveLength(1)
  finish()
  await screen.findByRole('button', { name: 'Save' })
})

it('retries a lost creation response with the same key and retains newer unsaved edits', async () => {
  await analyze()
  const normalFetch = fetchMock.getMockImplementation()!
  let loseResponse = true
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    const response = await normalFetch(url, init)
    if (url === '/api/drafts' && init?.method === 'POST' && loseResponse) { loseResponse = false; throw new Error('response lost') }
    return response
  })
  fireEvent.change(screen.getByLabelText('Editable reply to client'), { target: { value: 'First revision' } })
  fireEvent.click(screen.getByRole('button', { name: 'Create draft' }))
  await screen.findByRole('alert')
  expect((screen.getByLabelText('Editable reply to client') as HTMLTextAreaElement).value).toBe('First revision')
  fireEvent.change(screen.getByLabelText('Editable reply to client'), { target: { value: 'Newer revision' } })
  fireEvent.click(screen.getByRole('button', { name: 'Create draft' }))
  await screen.findByRole('button', { name: 'Save' })
  expect((screen.getByLabelText('Editable reply to client') as HTMLTextAreaElement).value).toBe('Newer revision')
  expect(screen.getByText('Unsaved changes')).toBeTruthy()
  const attempts = fetchMock.mock.calls.filter(([url, init]) => url === '/api/drafts' && init?.method === 'POST')
  expect(JSON.parse(String(attempts[0][1].body)).idempotencyKey).toBe(JSON.parse(String(attempts[1][1].body)).idempotencyKey)
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  await waitFor(() => expect(savedDocument.reply.text).toBe('Newer revision'))
})


it('preserves manual reply text when regenerating client-language materials', async () => {
  await analyze()
  const normalFetch = fetchMock.getMockImplementation()!
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    if (url === '/api/client-materials/language') return { ok: true, json: async () => ({ materials: {
      clientLanguage: 'en', replies: { warm: 'New warm', neutral: 'New neutral', firm: 'New firm' },
      changeOrder: { description: 'New scope', timelineImpact: 'Two days', rationale: 'Extra work', note: 'Draft' },
    } }) }
    return normalFetch(url, init)
  })
  fireEvent.change(screen.getByLabelText('Editable reply to client'), { target: { value: 'My negotiated reply' } })
  fireEvent.click(screen.getByRole('button', { name: en.result.applyClientLanguage }))
  await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => url === '/api/client-materials/language')).toBe(true))
  await waitFor(() => expect((screen.getByRole('button', { name: en.result.applyClientLanguage }) as HTMLButtonElement).disabled).toBe(false))
  expect((screen.getByLabelText('Editable reply to client') as HTMLTextAreaElement).value).toBe('My negotiated reply')
})

it('prepares an invalid estimate after the user creates a draft first', async () => {
  const normalFetch = fetchMock.getMockImplementation()!
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    if (url === '/api/analyze') return { ok: true, json: async () => ({ result: { ...analysisFixture, estimateValid: false } }) }
    if (url === '/api/change-orders/estimate') return { ok: true, json: async () => ({ result: { ...analysisFixture, changeOrder: { ...analysisFixture.changeOrder, additionalCost: '321' } } }) }
    return normalFetch(url, init)
  })
  const view = await analyze()
  fireEvent.click(screen.getByRole('button', { name: 'Create draft' }))
  await screen.findByRole('button', { name: 'Save' })
  view.unmount()
  app()
  await screen.findByText('Change order draft')
  fireEvent.change(document.querySelector('#co-description')!, { target: { value: 'Retained scope' } })
  fireEvent.click(screen.getByRole('button', { name: 'Create Change Order' }))
  await waitFor(() => expect((document.querySelector('#co-additionalCost') as HTMLInputElement)?.value).toBe('321'))
  expect((document.querySelector('#co-description') as HTMLTextAreaElement).value).toBe('Retained scope')
})

it('does not restore a delayed draft after navigation away', async () => {
  created = true
  const normalFetch = fetchMock.getMockImplementation()!
  let finish!: () => void
  const pending = new Promise<void>((resolve) => { finish = resolve })
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    if (url === '/api/drafts/d1') await pending
    return normalFetch(url, init)
  })
  app()
  await waitFor(() => expect((screen.getByText('Run') as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(screen.getByText('Drafts navigation'))
  fireEvent.click(await screen.findByRole('button', { name: /Add another page/ }))
  fireEvent.click(screen.getByText('History navigation'))
  await screen.findByText('Open saved draft')
  finish()
  await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => url === '/api/drafts/d1')).toBe(true))
  await new Promise((resolve) => setTimeout(resolve, 30))
  expect(screen.getByText('Open saved draft')).toBeTruthy()
  expect(document.querySelector('#co-description')).toBeNull()
})



it('redirects an unauthenticated workspace to login without logging an expected 401', async () => {
  const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
  try {
    fetchMock.mockImplementation(async () => ({ ok: false, status: 401, json: async () => ({ error: 'errors.authRequired' }) }))
    app()
    await waitFor(() => expect(navigation.router.replace).toHaveBeenCalledWith('/login'))
    expect(consoleError).not.toHaveBeenCalled()
  } finally { consoleError.mockRestore() }
})
