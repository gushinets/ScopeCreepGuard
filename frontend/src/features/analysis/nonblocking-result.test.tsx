// @vitest-environment jsdom
import { act, cleanup, fireEvent, render as testingRender, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { IntlProvider } from 'use-intl'
import en from '@/shared/i18n/messages/en.json'
import ru from '@/shared/i18n/messages/ru.json'
import { analysisFixture, documentFixture } from '@/features/drafts/model/fixtures'
import { ResultPanel } from '@/features/analysis/result-panel'

const state = vi.hoisted(() => ({ current: {} as Record<string, unknown> }))
vi.mock('./client-reply', () => ({ ClientReply: () => <div>Client replies</div> }))
vi.mock('./verdict-feedback', () => ({ VerdictFeedback: () => null }))
vi.mock('@/features/change-orders/change-order', () => ({ ChangeOrder: () => <div>Agreement editor</div> }))
afterEach(cleanup)

it.each(['en', 'ru'] as const)('prepares only on action and isolates failure in %s', async locale => {
  let fail!: () => void
  const prepareAgreement = vi.fn(() => new Promise<void>((_, reject) => { fail = () => reject(new Error('controlled failure')) }))
  const project = { id: 'p1', name: 'Project', startDate: '2026-10-01', pricingModel: 'hourly', currency: 'USD', hourlyRate: '30' }
  state.current = {
    status: 'result', result: { ...analysisFixture, changeOrder: null },
    selectedProject: project, analysisProject: project,
    projectSnapshot: { scope: 'Hidden historical scope' },
    draftDocument: { ...documentFixture, changeOrder: null },
    currentDraftId: 'd1', draftSessionId: 'd1', user: { id: 'u1' },
    workflow: { prepareAgreement, archived: false },
  }
  const messages = locale === 'ru' ? ru : en
  render(<IntlProvider locale={locale} messages={messages}><ResultPanel /></IntlProvider>)
  expect(prepareAgreement).not.toHaveBeenCalled()
  expect(screen.getByText(messages.result.whyHeading)).toBeTruthy()
  expect(screen.getByText(analysisFixture.reasoning)).toBeTruthy()
  expect(screen.getByText(analysisFixture.citations[0])).toBeTruthy()
  expect(screen.getByText(analysisFixture.suggestion!)).toBeTruthy()
  expect(screen.queryByText('Hidden historical scope')).toBeNull()
  expect(screen.queryByText('Agreement editor')).toBeNull()
  expect(screen.getByRole('tab', { name: 'Scope' }).getAttribute('aria-selected')).toBe('true')
  expect(screen.getAllByRole('tabpanel')).toHaveLength(1)
  fireEvent.click(screen.getByRole('tab', { name: messages.result.tabAgreement }))
  expect(prepareAgreement).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: messages.result.prepareAgreement }))
  expect(prepareAgreement).toHaveBeenCalledTimes(1)
  const busy = screen.getByRole('button', { name: messages.result.generatingChangeOrder }) as HTMLButtonElement
  expect(busy.disabled).toBe(true)
  fireEvent.click(busy)
  expect(prepareAgreement).toHaveBeenCalledTimes(1)
  await act(async () => { fail() })
  expect(screen.getByText('Client replies')).toBeTruthy()
  expect(screen.getByRole('alert').textContent).toBe(messages.result.changeOrderError)
  expect(screen.getByRole('button', { name: messages.result.prepareAgreement })).toBeTruthy()
  fireEvent.click(screen.getByRole('tab', { name: messages.result.tabReply }))
  expect(screen.getByRole('tabpanel').textContent).toContain('Client replies')
})

it('restores an existing agreement without provider work', () => {
  const prepareAgreement = vi.fn()
  state.current = {
    ...state.current, result: analysisFixture, draftDocument: documentFixture,
    workflow: { prepareAgreement, archived: false },
  }
  render(<IntlProvider locale="en" messages={en}><ResultPanel /></IntlProvider>)
  fireEvent.click(screen.getByRole('tab', { name: en.result.tabAgreement }))
  expect(screen.getByText('Agreement editor')).toBeTruthy()
  expect(prepareAgreement).not.toHaveBeenCalled()
  expect(screen.queryByRole('button', { name: en.result.prepareAgreement })).toBeNull()
})

it('supports keyboard navigation and keeps panels mounted without generating', () => {
  const prepareAgreement = vi.fn()
  state.current = { ...state.current, result: analysisFixture, draftDocument: documentFixture, workflow: { prepareAgreement, archived: false } }
  const view = render(<IntlProvider locale="en" messages={en}><ResultPanel /></IntlProvider>)
  const scope = screen.getByRole('tab', { name: 'Scope' })
  fireEvent.keyDown(scope, { key: 'ArrowRight' })
  const reply = screen.getByRole('tab', { name: en.result.tabReply })
  expect(document.activeElement).toBe(reply)
  expect(screen.getByRole('tabpanel').id).toBe('result-panel-reply')
  const select = screen.getByLabelText(en.result.documentLanguage) as HTMLSelectElement
  fireEvent.change(select, { target: { value: 'ru' } })
  fireEvent.keyDown(reply, { key: 'End' })
  expect(screen.getByRole('tabpanel').id).toBe('result-panel-agreement')
  fireEvent.keyDown(screen.getByRole('tab', { name: en.result.tabAgreement }), { key: 'ArrowLeft' })
  expect(screen.getByLabelText(en.result.documentLanguage)).toBe(select)
  expect(select.value).toBe('ru')
  // Ordinary result updates must not reset the selected panel.
  state.current = { ...state.current, result: { ...analysisFixture, clientLanguage: 'ru' } }
  view.rerender(<IntlProvider locale="en" messages={en}><ResultPanel /></IntlProvider>)
  expect(screen.getByRole('tabpanel').id).toBe('result-panel-reply')
  expect(prepareAgreement).not.toHaveBeenCalled()
  // A new check unmounts results while loading and starts at Scope.
  state.current = { ...state.current, status: 'loading' }
  view.rerender(<IntlProvider locale="en" messages={en}><ResultPanel /></IntlProvider>)
  state.current = { ...state.current, status: 'result' }
  view.rerender(<IntlProvider locale="en" messages={en}><ResultPanel /></IntlProvider>)
  expect(screen.getByRole('tabpanel').id).toBe('result-panel-scope')
})


import { StoreContext, type StoreValue } from '@/test/workspace'
function render(ui: React.ReactNode) { return testingRender(ui, { wrapper: ({ children }) => <StoreContext.Provider value={state.current as unknown as StoreValue}>{children}</StoreContext.Provider> }) }
