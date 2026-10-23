// @vitest-environment jsdom
import { cleanup, fireEvent, render as testingRender, screen, within } from '@testing-library/react'
import { IntlProvider } from 'use-intl'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import en from '@/shared/i18n/messages/en.json'
import ru from '@/shared/i18n/messages/ru.json'
import { workflowApi } from '@/features/drafts/model/workflow-client'
import type { ArchivedCheck, WorkingDraft } from '@/features/drafts/model/workflow-types'
import { PersistentHistoryView as CompactHistory, HistoryProjectDetails as PersistentHistoryView } from '@/features/history/persistent-history'
import { analysisFixture, documentFixture } from '@/features/drafts/model/fixtures'
const state = vi.hoisted(() => ({ complete: vi.fn(), restore: vi.fn(), history: [] as ArchivedCheck[], archives: vi.fn(), savedDraft: null as WorkingDraft | null }))
vi.mock('@/features/drafts/model/workflow-client', async importOriginal => ({ ...await importOriginal<typeof import('@/features/drafts/model/workflow-client')>(), workflowApi: vi.fn() }))
vi.mock('@/features/change-orders/change-order-document-preview', () => ({ ChangeOrderDocumentPreview: ({ draft }: { draft: { description?: string } }) => <div>Document preview{draft.description}</div> }))
beforeEach(() => { state.history = []; vi.mocked(workflowApi).mockReset(); state.complete.mockReset().mockResolvedValue(undefined); state.archives.mockReset().mockResolvedValue([]); state.savedDraft = { id: 'saved-draft', projectId: 'archived', revision: '4', requestText: 'Latest edited request', lastAnalysisRunId: null, analysisIsStale: true, analysisRun: null, createdAt: '2026-10-22T00:00:00Z', updatedAt: '2026-10-22T01:00:00Z', draftDocument: { version: 2, reply: { ...documentFixture.reply, language: 'en', text: 'Latest edited reply' }, changeOrder: { ...documentFixture.changeOrder!, description: 'Latest edited agreement' } } } })
afterEach(cleanup)
it.each([{ locale: 'en', messages: en }, { locale: 'ru', messages: ru }] as const)('renders the complete immutable assessment when history opens in $locale', async ({ locale, messages }) => {
 const analysis = { ...analysisFixture, changeOrder: null, estimate: { estimatedHours: 8, additionalCost: '240', currency: 'USD' as const } }
 const entry = { id: 'check', projectId: 'active', request: 'Saved client request', summary: analysis.summary, sourceKind: 'explicit', checkSnapshot: { version: 1, requestText: 'Saved client request', analysis, projectSnapshot: { scope: 'Frozen agreed scope' }, draftDocument: { reply: { text: 'Respuesta guardada' }, changeOrder: null } } } as ArchivedCheck
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

it.each([{ locale: 'en', messages: en }, { locale: 'ru', messages: ru }] as const)('does not require manual snapshot saving or finalization in $locale', ({ locale, messages }) => {
 render(<IntlProvider locale={locale} messages={messages}><PersistentHistoryView /></IntlProvider>)
 expect(screen.queryByRole('button', { name: messages.workflow.archiveEdits })).toBeNull()
 expect(screen.queryByRole('button', { name: messages.workflow.finalize })).toBeNull()
})

it.each([{ locale: 'en', messages: en }, { locale: 'ru', messages: ru }] as const)('keeps the latest autosaved draft accessible after archiving without creating a new check in $locale', async ({ locale, messages }) => {
 state.archives.mockResolvedValue([{ id: 'archived', name: 'Archived project', scope: 'Original agreed project deliverables', archivedAt: '2026-10-22', history: [] }])
 vi.mocked(workflowApi).mockResolvedValue({ draft: state.savedDraft })
 render(<IntlProvider locale={locale} messages={messages}><PersistentHistoryView projectId="archived" /></IntlProvider>)
 const latest = await screen.findByRole('article', { name: messages.history.savedDraft })
 for (const text of ['Latest edited request', 'Latest edited reply', 'Original agreed project deliverables']) expect(within(latest).getByText(text)).toBeTruthy()
 expect(within(latest).getByText(/Latest edited agreement/)).toBeTruthy()
 expect(within(latest).getByRole('button', { name: messages.changeOrder.downloadPdf })).toBeTruthy()
 expect(vi.mocked(workflowApi).mock.calls.every(([path, body]) => path === 'projects/archived/draft' && !body)).toBe(true)
})

import { StoreContext, type StoreValue } from '@/test/workspace'
function render(ui: React.ReactNode) { return testingRender(ui, { wrapper: ({ children }) => <StoreContext.Provider value={({ selectedProject: { id: 'active', name: 'Active project', history: state.history }, projects: [{ id: 'active', name: 'Active project', history: state.history }], archivedProjects: state.archives, restoreProject: state.restore, draftDocument: { changeOrder: {} }, workflow: { complete: state.complete } }) as unknown as StoreValue}>{children}</StoreContext.Provider> }) }

it.each([{ locale: 'en', messages: en }, { locale: 'ru', messages: ru }] as const)('opens an archived project directly in History without activating its draft in $locale', async ({ locale, messages }) => {
 const entry = { id: 'archived-check', projectId: 'archived', request: 'Archived request', summary: 'Archived check', sourceKind: 'explicit', checkSnapshot: { version: 1, requestText: 'Archived request', draftDocument: { reply: { text: 'Preserved reply' }, changeOrder: {} } } } as ArchivedCheck
 state.archives.mockResolvedValue([{ id: 'archived', name: 'Archived project', archivedAt: '2026-10-22', history: [entry] }])
 vi.mocked(workflowApi).mockImplementation(async path => {
  if (path === 'projects/archived/draft') return { draft: state.savedDraft }
  if (path === 'history/archived-check') return { entry }
  if (path.endsWith('/exports')) return { exports: [{ id: 'saved-pdf', status: 'ready', attemptCount: 1, errorCode: null }] }
  return { changeOrders: [{ id: 'preserved-agreement', reference: 'CO-preserved', revision: '1', status: 'finalized', contentSnapshot: { document: {} } }] }
 })
 render(<IntlProvider locale={locale} messages={messages}><PersistentHistoryView projectId="archived" /></IntlProvider>)
 await screen.findByRole('article', { name: messages.history.savedDraft })
 expect(screen.queryByRole('button', { name: messages.workflow.archiveEdits })).toBeNull()
 fireEvent.click(screen.getByRole('button', { name: messages.workflow.viewCheck }))
 await screen.findByText('Preserved reply')
 expect(screen.queryByRole('button', { name: messages.workflow.finalize })).toBeNull()
 await screen.findByText('CO-preserved')
 expect((screen.getByRole('button', { name: messages.workflow.exportPdf }) as HTMLButtonElement).disabled).toBe(true)
 expect((await screen.findByRole('button', { name: messages.workflow.download }) as HTMLButtonElement).disabled).toBe(false)
 expect(vi.mocked(workflowApi).mock.calls.every(([path, body]) => !body && !/^drafts\//.test(path))).toBe(true)
})

it('keeps active history usable when the archive list is unavailable', async () => {
 state.archives.mockRejectedValue(new Error('offline'))
 state.history = [{ id: 'saved', request: 'Active saved request', summary: 'Saved' } as ArchivedCheck]
 render(<IntlProvider locale="en" messages={en}><PersistentHistoryView /></IntlProvider>)
 await screen.findByRole('button', { name: en.workflow.viewCheck })
 expect(screen.getByRole('button', { name: en.workflow.viewCheck })).toBeTruthy()
})

it.each([{ locale: 'en', messages: en }, { locale: 'ru', messages: ru }] as const)('opens compact rows only on request and restores explicitly in $locale', async ({ locale, messages }) => {
 state.archives.mockResolvedValue([{ id: 'archived', name: 'Archived project', scope: 'Saved scope', archivedAt: '2026-10-22', history: [] }])
 state.restore.mockReset().mockResolvedValue(undefined)
 vi.mocked(workflowApi).mockResolvedValue({ draft: state.savedDraft })
 render(<IntlProvider locale={locale} messages={messages}><CompactHistory /></IntlProvider>)
 const row = await screen.findByRole('button', { name: /Archived project/ })
 expect(row.getAttribute('aria-expanded')).toBe('false')
 expect(workflowApi).not.toHaveBeenCalled()
 fireEvent.click(row)
 await screen.findByRole('article', { name: messages.history.savedDraft })
 expect(state.restore).not.toHaveBeenCalled()
 fireEvent.click(screen.getByRole('button', { name: messages.history.restoreProject }))
 await screen.findByRole('button', { name: /Active project/ })
 expect(state.restore).toHaveBeenCalledWith('archived')
})


it('does not substitute active history when the explicitly selected archive fails to load', async () => {
 state.archives.mockRejectedValue(new Error('offline'))
 state.history = [{ id: 'active-check', request: 'Unrelated active request', summary: 'Other project' } as ArchivedCheck]
 render(<IntlProvider locale="en" messages={en}><PersistentHistoryView projectId="missing-archive" /></IntlProvider>)
 await screen.findByRole('alert')
 expect(screen.queryByText('Unrelated active request')).toBeNull()
 expect(screen.queryByRole('button', { name: en.workflow.viewCheck })).toBeNull()
})
