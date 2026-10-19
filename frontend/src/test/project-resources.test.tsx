// @vitest-environment jsdom
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { IntlProvider } from 'use-intl'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import en from '@/shared/i18n/messages/en.json'
import { PersistentStoreProvider, useStore } from './workspace'
import { workflowFixture } from './workflow-fixture'
import { useProjectResources } from '@/features/projects'

let fixture: ReturnType<typeof workflowFixture>
beforeEach(() => { localStorage.clear(); sessionStorage.clear(); window.history.replaceState({}, '', '/'); fixture = workflowFixture() })
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
const wrapper = ({ children }: { children: ReactNode }) => <IntlProvider locale="en" messages={en}><PersistentStoreProvider>{children}</PersistentStoreProvider></IntlProvider>
const input = { name: 'Renamed website', clientName: 'Acme', industry: 'Design' as const, scope: 'Five pages', startDate: '2026-10-01', pricingModel: 'hourly' as const, currency: 'EUR' as const, hourlyRate: '120', fixedPrice: '' }
async function setup() {
  const hook = renderHook(useStore, { wrapper })
  await waitFor(() => expect(hook.result.current?.isLoadingProjects).toBe(false))
  return hook
}
it('persists contact/date updates in the server command and restores them without browser storage', async () => {
  const hook = await setup()
  await act(async () => { await hook.result.current.updateProject('p1', input, { clientName: 'Acme', clientEmail: 'acme@example.test', endDate: '2027-01-15' }) })
  expect(fixture.state.calls.find(call => call.method === 'PATCH')?.body).toMatchObject({ expectedRevision: '3', clientEmail: 'acme@example.test', endDate: '2027-01-15' })
  hook.unmount(); localStorage.clear()
  const reloaded = await setup()
  expect(reloaded.result.current.selectedProject).toMatchObject({ name: 'Renamed website', clientEmail: 'acme@example.test', endDate: '2027-01-15' })
})
it('ignores obsolete browser-only project/analysis details in favor of the server resource', async () => {
  localStorage.setItem('scg:project:u1:p1', JSON.stringify({ clientName: 'Stale client', clientEmail: 'stale@example.test' }))
  const hook = await setup()
  expect(hook.result.current.selectedProject?.clientEmail).toBe('client@example.test')
  expect(hook.result.current.result?.reasoning).toBe('Not included')
})
it('creates a project with server-owned optional details and activates its one working Draft', async () => {
  const hook = await setup()
  await act(async () => { await hook.result.current.createProject({ ...input, clientEmail: 'new@example.test', endDate: '2027-02-01' }) })
  expect(hook.result.current.currentDraftId).toBe('d2')
  expect(hook.result.current.selectedProject).toMatchObject({ clientEmail: 'new@example.test', endDate: '2027-02-01' })
  expect(new URL(window.location.href).searchParams.get('draft')).toBe('d2')
})
it('retains active data and the URL when project archival fails', async () => {
  const hook = await setup()
  fixture.state.failure = '/api/v2/projects/p1'
  await act(async () => { await expect(hook.result.current.deleteProject('p1')).rejects.toThrow() })
  expect(hook.result.current.currentDraftId).toBe('d1')
  expect(hook.result.current.selectedProject?.name).toBe('Website')
  expect(new URL(window.location.href).searchParams.get('draft')).toBe('d1')
})
it('archives the last project without retaining a dangling Draft or stale analysis', async () => {
  const hook = await setup()
  await act(async () => { await hook.result.current.deleteProject('p1') })
  expect(hook.result.current.projects).toHaveLength(0)
  expect(hook.result.current.currentDraftId).toBeNull()
  expect(hook.result.current.result).toBeNull()
  expect(new URL(window.location.href).searchParams.has('draft')).toBe(false)
})

it('does not let an older resource fetch overwrite a newer confirmed project mutation', async () => {
  let release!: (response: Response) => void
  const pending = new Promise<Response>(resolve => { release = resolve })
  fixture.fetcher.mockImplementationOnce(() => pending)
  const hook = renderHook(useProjectResources)
  let reload!: Promise<unknown>
  act(() => { reload = hook.result.current.reload() })
  act(() => hook.result.current.upsert({ ...fixture.project, name: 'Confirmed newer name' }))
  await act(async () => { release(Response.json({ projects: [fixture.project] })); await reload })
  expect(hook.result.current.projects[0].name).toBe('Confirmed newer name')
})
