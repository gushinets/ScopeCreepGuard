// @vitest-environment jsdom
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { IntlProvider } from 'use-intl'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import en from '@/shared/i18n/messages/en.json'
import { PersistentStoreProvider, useStore } from './workspace'
import { workflowFixture } from './workflow-fixture'

let fixture: ReturnType<typeof workflowFixture>
beforeEach(() => { localStorage.clear(); sessionStorage.clear(); window.history.replaceState({}, '', '/'); fixture = workflowFixture(); vi.spyOn(window, 'confirm').mockReturnValue(true) })
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals() })
const wrapper = ({ children }: { children: ReactNode }) => <IntlProvider locale="en" messages={en}><PersistentStoreProvider>{children}</PersistentStoreProvider></IntlProvider>
async function setup() { const hook = renderHook(useStore, { wrapper }); await waitFor(() => expect(hook.result.current?.isLoadingProjects).toBe(false)); return hook }
it('translates through the versioned command with saved manual commercial values intact', async () => {
  const hook = await setup()
  const before = structuredClone(hook.result.current.draftDocument!.changeOrder)
  await act(async () => { await hook.result.current.changeClientLanguage('pt-BR') })
  expect(hook.result.current.result?.clientLanguage).toBe('pt-BR')
  expect(hook.result.current.draftDocument?.changeOrder).toEqual(before)
  expect(fixture.state.calls.find(call => call.path.endsWith('/translate'))?.body).toMatchObject({ language: 'pt-BR', expectedRevision: '3' })
  expect(fixture.state.calls.some(call => call.path === '/api/client-materials/language')).toBe(false)
})
it('cancelling manual-material replacement preserves the editor without dispatching translation', async () => {
  const hook = await setup()
  vi.mocked(window.confirm).mockReturnValue(false)
  await act(async () => { expect(await hook.result.current.changeClientLanguage('de')).toBe(true) })
  expect(hook.result.current.result?.clientLanguage).toBe('es')
  expect(fixture.state.calls.some(call => call.path.endsWith('/translate'))).toBe(false)
})
it('restores manual language selection from the server after a storage-free remount', async () => {
  const first = await setup()
  await act(async () => { await first.result.current.changeClientLanguage('de') })
  first.unmount(); localStorage.clear(); sessionStorage.clear()
  const reopened = await setup()
  expect(reopened.result.current.result?.clientLanguage).toBe('de')
  expect(reopened.result.current.draftDocument?.languageSelection?.override).toBe(true)
})
it('regenerates only the saved selected tone and preserves original assessment and agreement', async () => {
  const hook = await setup()
  const original = structuredClone(fixture.state.drafts.get('d1')!)
  await act(async () => { await hook.result.current.workflow.regenerate() })
  expect(hook.result.current.draftDocument?.reply.generated).toEqual({ ...original.draftDocument.reply.generated, firm: 'Regenerated selected reply' })
  expect(hook.result.current.result?.reasoning).toBe('Not included')
  expect(hook.result.current.draftDocument?.changeOrder).toEqual(original.draftDocument.changeOrder)
})
