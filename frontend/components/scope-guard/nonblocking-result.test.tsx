// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { NextIntlClientProvider } from 'next-intl'
import en from '@/messages/en.json'
import ru from '@/messages/ru.json'
import { analysisFixture, documentFixture } from '@/lib/drafts/fixtures'
import { ResultPanel } from './result-panel'

const state = vi.hoisted(() => ({ current: {} as Record<string, unknown> }))
vi.mock('./store', () => ({ useStore: () => state.current }))
vi.mock('./client-reply', () => ({ ClientReply: () => <div>Client replies</div> }))
vi.mock('./verdict-feedback', () => ({ VerdictFeedback: () => null }))
vi.mock('./change-order', () => ({ ChangeOrder: () => <div>Agreement editor</div> }))
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
  render(<NextIntlClientProvider locale={locale} messages={messages}><ResultPanel /></NextIntlClientProvider>)
  expect(prepareAgreement).not.toHaveBeenCalled()
  expect(screen.queryByText(messages.result.whyHeading)).toBeNull()
  expect(screen.queryByText('Hidden historical scope')).toBeNull()
  expect(screen.queryByText('Agreement editor')).toBeNull()
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
})

it('restores an existing agreement without provider work', () => {
  const prepareAgreement = vi.fn()
  state.current = {
    ...state.current, result: analysisFixture, draftDocument: documentFixture,
    workflow: { prepareAgreement, archived: false },
  }
  render(<NextIntlClientProvider locale="en" messages={en}><ResultPanel /></NextIntlClientProvider>)
  expect(screen.getByText('Agreement editor')).toBeTruthy()
  expect(prepareAgreement).not.toHaveBeenCalled()
  expect(screen.queryByRole('button', { name: en.result.prepareAgreement })).toBeNull()
})
