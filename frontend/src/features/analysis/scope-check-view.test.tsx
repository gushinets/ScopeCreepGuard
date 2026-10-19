// @vitest-environment jsdom
import { render, screen } from '@testing-library/react'
import { IntlProvider } from 'use-intl'
import { expect, it } from 'vitest'
import en from '@/shared/i18n/messages/en.json'
import type { StoreValue } from '@/test/workspace'
import { StoreContext } from '@/test/workspace'
import { ScopeCheckView } from '@/features/analysis/scope-check-view'

it('does not render Draft synchronization controls in the user workspace', () => {
  render(<IntlProvider locale="en" messages={en}><StoreContext.Provider value={{
    workflow: { status: 'conflict', stale: false, recovery: null, archived: false }, selectedProject: null,
  } as unknown as StoreValue}><ScopeCheckView /></StoreContext.Provider></IntlProvider>)
  expect(screen.queryByText(en.workflow.saved)).toBeNull()
  expect(screen.queryByRole('button', { name: en.workflow.complete })).toBeNull()
  expect(screen.queryByText(en.workflow.conflict)).toBeNull()
})
