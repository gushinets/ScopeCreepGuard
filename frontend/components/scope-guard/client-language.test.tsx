// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { germanLabels } from '@/lib/change-order/german-fixture'
import { commercialSignature } from '@/lib/change-order/commercial-signature'
import type { SavedDraft } from '@/lib/drafts/types'
import type { AnalysisResult, Project } from '@/lib/types'
import { ResultPanel } from './result-panel'
import { StoreProvider, useStore } from './store'

const mocks = vi.hoisted(() => ({ router: { replace: vi.fn() } }))
vi.mock('next/navigation', () => ({ useRouter: () => mocks.router }))
vi.mock('next-intl', () => ({ useLocale: () => 'ru', useTranslations: () => (key: string) => key }))
vi.mock('./verdict-feedback', () => ({ VerdictFeedback: () => null }))
vi.mock('./verdict', () => ({ VerdictBanner: ({ summary, verdict, confidence }: AnalysisResult) => <p>{summary}: {verdict}: {confidence}</p> }))
vi.mock('./client-reply', () => ({ ClientReply: ({ result }: { result: AnalysisResult }) => <p>{result.replies.neutral}</p> }))
vi.mock('./change-order', () => ({ ChangeOrder: ({ result }: { result: AnalysisResult }) => <p>{result.clientLanguage}: {result.changeOrder.description}: {result.changeOrder.additionalCost}: {result.changeOrder.estimatedHours}: {result.changeOrder.currency}</p> }))

const original: AnalysisResult = {
  verdict: 'out_of_scope', confidence: 90, summary: 'Русское резюме', reasoning: 'Русское обоснование', suggestion: 'Русская рекомендация', citations: ['Five pages'],
  clientLanguage: 'en', replies: { warm: 'Hello', neutral: 'Extra work', firm: 'Approve first' },
  changeOrder: { description: 'Extra page', timelineImpact: 'Two days', additionalCost: '200', estimatedHours: 2, currency: 'EUR', rationale: 'Extra work', note: 'Draft' },
  hasAdditionalWork: true, estimateValid: true, draftCreatedAt: '2026-10-06',
}
let project: Project
let savedDraft: SavedDraft | null = null
const fetchMock = vi.fn()
const materials = {
  clientLanguage: 'de', replies: { warm: 'Danke', neutral: 'Zusätzliche Arbeiten', firm: 'Bitte genehmigen' },
  changeOrder: { description: 'Neue Seite', timelineImpact: 'Zwei Tage', rationale: 'Zusätzliche Leistung', note: 'Entwurf', additionalCost: '99999', estimatedHours: 999 },
  changeOrderLabels: germanLabels, verdict: 'in_scope', hasAdditionalWork: false, confidence: 1,
}

beforeEach(() => {
  localStorage.clear()
  window.history.replaceState({}, '', '/')
  savedDraft = null
  fetchMock.mockReset()
  project = { id: 'p1', name: 'Website', industry: 'Development', scope: 'Build exactly five marketing pages. Additional pages are outside the agreed scope.', startDate: '2026-01-01', pricingModel: 'hourly', currency: 'EUR', hourlyRate: '100', fixedPrice: null, history: [] }
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    let body
    if (url === '/api/auth/me') body = { user: { id: 'u1', email: 'u@example.com' } }
    else if (url === '/api/projects') body = { projects: [project] }
    else if (url === '/api/analyze') body = { result: { ...original, commercialSignature: commercialSignature(project) }, proof: 'signed-language-proof', projectSnapshot: { version: 1, ...project, endDate: null, documentLanguage: null } }
    else if (url === '/api/drafts' && init?.method === 'POST') {
      const input = JSON.parse(String(init.body))
      const entry = { id: 'h1', draftId: 'd1', date: '2026-10-06', request: 'Add a page', verdict: original.verdict, summary: original.summary }
      project = { ...project, history: [entry] }
      savedDraft = { id: 'd1', projectId: 'p1', historyEntryId: 'h1', request: input.request, status: 'draft', createdAt: original.draftCreatedAt!, updatedAt: original.draftCreatedAt!, locale: 'ru', requestLanguage: null, clientMaterialLanguage: 'de', projectSnapshot: { version: 1, name: project.name, industry: project.industry, scope: project.scope, startDate: project.startDate, endDate: null, pricingModel: project.pricingModel, currency: project.currency, hourlyRate: project.hourlyRate, fixedPrice: project.fixedPrice, documentLanguage: null }, analysisSnapshot: original, draftDocument: input.draftDocument }
      body = { draft: savedDraft, entry }
    } else if (url === '/api/drafts/d1') { body = { draft: savedDraft }
    } else if (url === '/api/client-materials/language') body = { materials }
    else if (url === '/api/change-orders/estimate') body = { result: original }
    else throw new Error(`Unexpected API: ${url}`)
    return { ok: true, json: async () => body }
  })
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.clearAllMocks() })

function Controls() {
  const store = useStore()
  return <><input aria-label="Request" value={store.requestText} onChange={(e) => store.setRequestText(e.target.value)} /><button onClick={store.runCheck} disabled={!store.selectedProject}>Run</button><button onClick={() => { if (store.draftDocument?.changeOrder) store.updateChangeOrder({ ...store.draftDocument.changeOrder, description: 'Custom scope', additionalCost: '175', note: '' }) }}>Edit terms</button><pre data-testid="document">{JSON.stringify(store.draftDocument)}</pre></>
}
function app() { return render(<StoreProvider><Controls /><ResultPanel /></StoreProvider>) }
async function analyze() {
  const view = app()
  await waitFor(() => expect((screen.getByRole('button', { name: 'Run' }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.change(screen.getByLabelText('Request'), { target: { value: 'Add a page' } })
  fireEvent.click(screen.getByRole('button', { name: 'Run' }))
  await screen.findByText('Extra work')
  return view
}
async function override() {
  fireEvent.change(screen.getByLabelText('result.documentLanguage'), { target: { value: 'DE' } })
  fireEvent.click(screen.getByRole('button', { name: 'result.applyClientLanguage' }))
  await screen.findByText('Zusätzliche Arbeiten')
}

it('uses only the dedicated language endpoint and preserves scope and monetary values', async () => {
  await analyze()
  await override()
  const calls = fetchMock.mock.calls.map(([url]) => url)
  expect(calls).toContain('/api/client-materials/language')
  expect(calls).not.toContain('/api/change-orders/estimate')
  expect(calls.filter((url) => url === '/api/analyze')).toHaveLength(1)
  expect(screen.getByText('Русское резюме: out_of_scope: 90')).toBeTruthy()
  expect(screen.getByText('Русское обоснование')).toBeTruthy()
  expect(screen.getByText('Русская рекомендация')).toBeTruthy()
  expect(screen.getByText('Five pages')).toBeTruthy()
  const stored = JSON.parse(screen.getByTestId('document').textContent!)
  expect(stored.result.changeOrder.additionalCost).toBe('200')
  expect(stored.result.hasAdditionalWork).toBe(true)
  expect(stored.clientMaterials.changeOrder.additionalCost).toBeUndefined()
  expect(localStorage.getItem('scg:client-materials:u1:p1:h1')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'result.createChangeOrder' }))
  await screen.findByText('de: Neue Seite: 200: 2: EUR')
  expect(fetchMock.mock.calls.some(([url]) => url === '/api/change-orders/estimate')).toBe(false)
})

it('restores explicitly created client materials from the server after reload', async () => {
  const view = await analyze()
  await override()
  fireEvent.click(screen.getByRole('button', { name: 'drafts.create' }))
  await screen.findByRole('button', { name: 'drafts.save' })
  view.unmount()
  localStorage.clear()
  app()
  await screen.findByText('Zusätzliche Arbeiten')
  expect((screen.getByLabelText('result.documentLanguage') as HTMLInputElement).value).toBe('de')
  expect(screen.getByText('Русское резюме: out_of_scope: 90')).toBeTruthy()
  expect(fetchMock.mock.calls.filter(([url]) => url === '/api/analyze')).toHaveLength(1)
})

it('rejects unsupported scripts accessibly before sending a generation request', async () => {
  await analyze()
  const input = screen.getByLabelText('result.documentLanguage')
  fireEvent.change(input, { target: { value: 'ar' } })
  expect(input.getAttribute('aria-invalid')).toBe('true')
  expect(screen.getByRole('alert').textContent).toBe('errors.clientLanguageUnsupported')
  expect((screen.getByRole('button', { name: 'result.applyClientLanguage' }) as HTMLButtonElement).disabled).toBe(true)
  expect(fetchMock.mock.calls.some(([url]) => url === '/api/client-materials/language')).toBe(false)
})

it('updates a closed saved draft without overwriting user changes on repeated overrides', async () => {
  await analyze()
  fireEvent.click(screen.getByText('Edit terms'))
  await override()
  expect(JSON.parse(screen.getByTestId('document').textContent!).changeOrder).toMatchObject({ language: 'de', description: 'Custom scope', timelineImpact: 'Zwei Tage', additionalCost: '175', note: '' })
  // Regenerate again in the same selected language.
  fireEvent.click(screen.getByRole('button', { name: 'result.applyClientLanguage' }))
  await waitFor(() => expect(fetchMock.mock.calls.filter(([url]) => url === '/api/client-materials/language')).toHaveLength(2))
  expect(JSON.parse(screen.getByTestId('document').textContent!).changeOrder).toMatchObject({ description: 'Custom scope', additionalCost: '175', note: '' })
  expect(fetchMock.mock.calls.some(([url]) => url === '/api/change-orders/estimate')).toBe(false)
})
