// @vitest-environment jsdom
import { render, screen } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { expect, it } from 'vitest'
import en from '@/messages/en.json'
import type { StoreValue } from './store'
import { StoreContext } from './store'
import { ScopeCheckView } from './scope-check-view'

it('does not render Draft synchronization controls in the user workspace', () => {
  render(<NextIntlClientProvider locale="en" messages={en}><StoreContext.Provider value={{
    workflow: { status: 'conflict', stale: false, recovery: null, archived: false }, selectedProject: null,
  } as unknown as StoreValue}><ScopeCheckView /></StoreContext.Provider></NextIntlClientProvider>)
  expect(screen.queryByText(en.workflow.saved)).toBeNull()
  expect(screen.queryByRole('button', { name: en.workflow.complete })).toBeNull()
  expect(screen.queryByText(en.workflow.conflict)).toBeNull()
})
