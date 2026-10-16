// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import en from '@/messages/en.json'
import ru from '@/messages/ru.json'
import { workflowApi, WorkflowApiError } from '@/lib/drafts/workflow-client'
import type { ArchivedCheck } from '@/lib/drafts/workflow-types'
import { PersistentHistoryView } from './persistent-history'
const state = vi.hoisted(() => ({ complete: vi.fn(), history: [] as ArchivedCheck[] }))
vi.mock('./store', () => ({ useStore: () => ({ selectedProject: { history: state.history }, draftDocument: { changeOrder: {} }, workflow: { complete: state.complete } }) }))
vi.mock('@/lib/drafts/workflow-client', async importOriginal => ({ ...await importOriginal<typeof import('@/lib/drafts/workflow-client')>(), workflowApi: vi.fn() }))
vi.mock('./change-order-document-preview', () => ({ ChangeOrderDocumentPreview: () => <div>Document preview</div> }))
beforeEach(() => { state.history = []; vi.mocked(workflowApi).mockReset(); state.complete.mockReset().mockResolvedValue(undefined) })
afterEach(cleanup)
it.each([{ locale: 'en', messages: en, label: 'Archive current document edits' }, { locale: 'ru', messages: ru, label: 'Сохранить правки документа в Историю' }] as const)('archives edited material through the existing durable action in $locale', async ({ locale, messages, label }) => {
 let finish!: () => void
 state.complete.mockImplementation(() => new Promise<void>(resolve => { finish = resolve }))
 render(<NextIntlClientProvider locale={locale} messages={messages}><PersistentHistoryView /></NextIntlClientProvider>)
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
 render(<NextIntlClientProvider locale={locale} messages={messages}><PersistentHistoryView /></NextIntlClientProvider>)
 fireEvent.click(screen.getByRole('button', { name: messages.workflow.viewCheck }))
 fireEvent.click(await screen.findByRole('button', { name: messages.workflow.finalize }))
 for (const field of ['hoursLabel', 'costLabel'] as const) {
  await screen.findByText(messages.changeOrder.readiness.positive.replace('{field}', messages.changeOrder[field]))
  expect(screen.queryByText(messages.changeOrder.readiness.required.replace('{field}', messages.changeOrder[field]))).toBeNull()
 }
 expect(screen.getByText(messages.changeOrder.readiness.required.replace('{field}', messages.changeOrder.descriptionLabel))).toBeTruthy()
})
