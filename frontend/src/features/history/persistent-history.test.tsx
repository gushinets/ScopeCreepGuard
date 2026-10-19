// @vitest-environment jsdom
import { cleanup, fireEvent, render as testingRender, screen, waitFor, within } from '@testing-library/react'
import { IntlProvider } from 'use-intl'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import en from '@/shared/i18n/messages/en.json'
import ru from '@/shared/i18n/messages/ru.json'
import { workflowApi, WorkflowApiError } from '@/features/drafts/model/workflow-client'
import type { ArchivedCheck } from '@/features/drafts/model/workflow-types'
import { PersistentHistoryView } from '@/features/history/persistent-history'
import { analysisFixture } from '@/features/drafts/model/fixtures'
const state = vi.hoisted(() => ({ complete: vi.fn(), history: [] as ArchivedCheck[] }))
vi.mock('@/features/drafts/model/workflow-client', async importOriginal => ({ ...await importOriginal<typeof import('@/features/drafts/model/workflow-client')>(), workflowApi: vi.fn() }))
vi.mock('@/features/change-orders/change-order-document-preview', () => ({ ChangeOrderDocumentPreview: () => <div>Document preview</div> }))
beforeEach(() => { state.history = []; vi.mocked(workflowApi).mockReset(); state.complete.mockReset().mockResolvedValue(undefined) })
afterEach(cleanup)
it.each([{ locale: 'en', messages: en }, { locale: 'ru', messages: ru }] as const)('renders the complete immutable assessment when history opens in $locale', async ({ locale, messages }) => {
 const analysis = { ...analysisFixture, changeOrder: null, estimate: { estimatedHours: 8, additionalCost: '240', currency: 'USD' as const } }
 const entry = { id: 'check', request: 'Saved client request', summary: analysis.summary, sourceKind: 'explicit', checkSnapshot: { version: 1, requestText: 'Saved client request', analysis, projectSnapshot: { scope: 'Frozen agreed scope' }, draftDocument: { reply: { text: 'Respuesta guardada' }, changeOrder: null } } } as ArchivedCheck
 const before = structuredClone(entry)
 state.history = [entry]
 vi.mocked(workflowApi).mockImplementation(async path => path === 'history/check' ? { entry } : { changeOrders: [] })
 render(<IntlProvider locale={locale} messages={messages}><PersistentHistoryView /></IntlProvider>)
 fireEvent.click(screen.getByRole('button', { name: messages.workflow.viewCheck }))
 const assessment = await screen.findByRole('region', { name: messages.result.whyHeading })
 for (const text of [analysis.reasoning, analysis.citations[0], analysis.suggestion!, messages.result.preliminaryEstimate, messages.result.nextStep]) expect(within(assessment).getByText(text)).toBeTruthy()
 expect(within(assessment).getByText('8')).toBeTruthy()
 expect(within(assessment).getByText((_, el) => el?.tagName === 'DD' && el.textContent === new Intl.NumberFormat(locale, { style: 'currency', currency: 'USD' }).format(240))).toBeTruthy()
 expect(screen.getByText(/90/)).toBeTruthy()
 expect(screen.getByText('Respuesta guardada')).toBeTruthy()
 expect(screen.queryByRole('button', { name: messages.result.createChangeOrder })).toBeNull()
 expect(entry).toEqual(before)
})

it.each([{ locale: 'en', messages: en, label: 'Archive current document edits' }, { locale: 'ru', messages: ru, label: 'Сохранить правки документа в Историю' }] as const)('archives edited material through the existing durable action in $locale', async ({ locale, messages, label }) => {
 let finish!: () => void
 state.complete.mockImplementation(() => new Promise<void>(resolve => { finish = resolve }))
 render(<IntlProvider locale={locale} messages={messages}><PersistentHistoryView /></IntlProvider>)
 const action = screen.getByRole('button', { name: label }) as HTMLButtonElement
 fireEvent.click(action)
 expect(action.disabled).toBe(true)
 expect(state.complete).toHaveBeenCalledTimes(1)
 finish()
 await waitFor(() => expect(action.disabled).toBe(false))
})

it.each([{ locale: 'en', messages: en }, { locale: 'ru', messages: ru }] as const)('keeps positive and required finalization guidance distinct in $locale', async ({ locale, messages }) => {
 const entry = { id: 'check', request: 'Synthetic request', summary: 'Synthetic check', sourceKind: 'explicit', checkSnapshot: { version: 1, draftDocument: { reply: { text: '' }, changeOrder: {} } } } as ArchivedCheck
 state.history = [entry]
 vi.mocked(workflowApi).mockImplementation(async (path, body) => {
  if (path === 'history/check') return { entry }
  if (!body) return { changeOrders: [] }
  throw new WorkflowApiError('errors.documentInvalid', 422, false, { estimatedHours: 'positive', additionalCost: 'positive', description: 'required' })
 })
 render(<IntlProvider locale={locale} messages={messages}><PersistentHistoryView /></IntlProvider>)
 fireEvent.click(screen.getByRole('button', { name: messages.workflow.viewCheck }))
 fireEvent.click(await screen.findByRole('button', { name: messages.workflow.finalize }))
 for (const field of ['hoursLabel', 'costLabel'] as const) {
  await screen.findByText(messages.changeOrder.readiness.positive.replace('{field}', messages.changeOrder[field]))
  expect(screen.queryByText(messages.changeOrder.readiness.required.replace('{field}', messages.changeOrder[field]))).toBeNull()
 }
 expect(screen.getByText(messages.changeOrder.readiness.required.replace('{field}', messages.changeOrder.descriptionLabel))).toBeTruthy()
})


import { StoreContext, type StoreValue } from '@/test/workspace'
function render(ui: React.ReactNode) { return testingRender(ui, { wrapper: ({ children }) => <StoreContext.Provider value={({ selectedProject: { history: state.history }, draftDocument: { changeOrder: {} }, workflow: { complete: state.complete } }) as unknown as StoreValue}>{children}</StoreContext.Provider> }) }
