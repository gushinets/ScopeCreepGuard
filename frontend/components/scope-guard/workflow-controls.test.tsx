// @vitest-environment jsdom
import { fireEvent, render, screen } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { expect, it, vi } from 'vitest'
import en from '@/messages/en.json'
import type { StoreValue } from './store'
import { StoreContext } from './store'
import { WorkflowControls } from './workflow-controls'

function renderControls(overrides: Partial<StoreValue['workflow']> = {}) {
  const retrySave = vi.fn(async () => {})
  const complete = vi.fn(async () => {})
  const workflow = {
    status: 'saved', stale: false, recovery: null, archived: false,
    acceptRecovery: vi.fn(), discardRecovery: vi.fn(), resolveConflict: vi.fn(), compareConflict: vi.fn(),
    legacyRevision: null, closeLegacy: vi.fn(), archivedProjects: vi.fn(), openArchived: vi.fn(),
    regenerate: vi.fn(), complete, retrySave,
    ...overrides,
  }
  const view = render(<NextIntlClientProvider locale="en" messages={en}><StoreContext.Provider value={{
    workflow, currentDraftId: 'd1', currentHistoryEntryId: null, draftError: '', result: null,
  } as unknown as StoreValue}><WorkflowControls /></StoreContext.Provider></NextIntlClientProvider>)
  return { view, workflow, retrySave, complete }
}

it('shows one autosave status without manual-save or revision-management controls', () => {
  renderControls()
  expect(screen.getAllByRole('status')).toHaveLength(1)
  expect(screen.getByRole('status').textContent).toBe(en.workflow.saved)
  expect(screen.queryByRole('button', { name: 'Save Draft now' })).toBeNull()
  expect(screen.queryByRole('button', { name: 'Working revisions' })).toBeNull()
  expect(screen.queryByRole('button', { name: 'Restore as a new revision' })).toBeNull()
})

it('retries only a failed autosave operation', async () => {
  const { retrySave } = renderControls({ status: 'failed' })
  fireEvent.click(screen.getByRole('button', { name: en.workflow.retrySave }))
  expect(retrySave).toHaveBeenCalledOnce()
})

it('hides conflict and recovery implementation details from users', () => {
  const { view } = renderControls({
    status: 'conflict',
    recovery: { version: 1, draftId: 'd1', baseRevision: '1', changes: { requestText: 'local', draftDocument: { version: 2, reply: { text: '', tone: 'neutral', language: 'en', generated: { warm: '', neutral: '', firm: '' } }, changeOrder: null } }, attempt: null },
  })
  expect(view.container.innerHTML).toBe('')
})
