// @vitest-environment jsdom
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'
import { NextIntlClientProvider } from 'next-intl'
import en from '@/messages/en.json'
import type { Project } from '@/lib/types'
import { analysisFixture, documentFixture, projectSnapshotFixture } from '@/lib/drafts/fixtures'
import { StoreProvider, useStore } from './store'
const router = { replace: vi.fn() }
vi.mock('next/navigation', () => ({ useRouter: () => router }))
const project: Project = { id: 'p1', name: 'Website', clientName: 'Server client', industry: 'Development', scope: 'Build exactly five pages with desktop and mobile layouts and one revision.', startDate: '2026-01-01', pricingModel: 'hourly', currency: 'EUR', hourlyRate: '100.00', fixedPrice: null, history: [] }
const saved = { id: 'd1', projectId: 'p1', historyEntryId: 'h1', request: 'Add a page', status: 'draft', createdAt: '2026-10-06T12:00:00.000Z', updatedAt: '2026-10-06T12:00:00.000Z', locale: 'en', clientMaterialLanguage: 'en', projectSnapshot: { ...projectSnapshotFixture, clientName: 'Historical client', endDate: '2026-12-01' }, analysisSnapshot: analysisFixture, draftDocument: documentFixture }
let projects: Project[]
let override: ((url: string, init?: RequestInit) => Promise<Response> | null) | undefined
const json = (value: unknown) => Promise.resolve(Response.json(value))
beforeEach(() => {
  localStorage.clear()
  window.history.replaceState({}, '', '/')
  projects = [structuredClone(project), { ...structuredClone(project), id: 'p2', name: 'Other project' }]
  override = undefined
  vi.stubGlobal('fetch', vi.fn((url: string, init?: RequestInit) => {
    const response = override?.(url, init)
    if (response) return response
    if (url === '/api/auth/me') return json({ user: { id: 'u1', email: 'owner@example.test' } })
    if (url === '/api/projects') return json({ projects })
    if (init?.method === 'PATCH') {
      const body = JSON.parse(String(init.body))
      const updated = { ...projects[0], ...body, hourlyRate: body.pricingModel === 'hourly' ? Number(body.hourlyRate).toFixed(2) : null, fixedPrice: body.pricingModel === 'fixed' ? Number(body.fixedPrice).toFixed(2) : null }
      projects = projects.map(p => p.id === 'p1' ? updated : p)
      return json({ project: updated })
    }
    if (init?.method === 'DELETE') { projects = projects.filter(p => !url.endsWith(p.id)); return json({ ok: true }) }
    if (url === '/api/analyze') return json({ result: analysisFixture, proof: 'signed-proof', projectSnapshot: { ...projectSnapshotFixture, clientName: projects[0].clientName, name: projects[0].name, scope: projects[0].scope, endDate: JSON.parse(String(init?.body)).endDate ?? null } })
    if (url === '/api/drafts/d1') return json({ draft: structuredClone(saved) })
    if (url === '/api/drafts' && init?.method === 'POST') return json({ draft: { ...saved, draftDocument: JSON.parse(String(init.body)).draftDocument }, entry: { id: 'h1', draftId: 'd1', date: '2026-10-07', request: 'Add a page', verdict: 'out_of_scope', summary: 'Extra page' } })
    if (url === '/api/change-orders/estimate') return json({ result: analysisFixture })
    throw new Error('Unexpected request: ' + url)
  }))
})
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
const input = () => ({ name: project.name, clientName: project.clientName!, industry: project.industry, scope: project.scope, startDate: project.startDate!, pricingModel: project.pricingModel!, currency: project.currency!, hourlyRate: project.hourlyRate!, fixedPrice: '' })
async function setup(analyze = true) {
  const hook = renderHook(() => useStore(), { wrapper: ({ children }: { children: ReactNode }) => <NextIntlClientProvider locale="en" messages={en}><StoreProvider>{children}</StoreProvider></NextIntlClientProvider> })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  if (analyze) {
    act(() => hook.result.current.setRequestText('Add a page'))
    act(() => hook.result.current.runCheck())
    await waitFor(() => expect(hook.result.current.status).toBe('result'))
  }
  return hook
}
it.each([
  ['scope', 'New agreed scope'], ['industry', 'Marketing'], ['startDate', '2026-10-07'],
  ['currency', 'USD'], ['hourlyRate', '125'], ['pricingModel', 'fixed'],
] as const)('clears only unsaved document and proof after changing %s', async (field, value) => {
  const { result } = await setup()
  await act(async () => { await result.current.updateProject('p1', { ...input(), [field]: value, ...(field === 'pricingModel' ? { fixedPrice: '5000' } : {}) }) })
  expect(result.current.result).toBeNull()
  expect(result.current.draftDocument).toBeNull()
  expect(result.current.projectSnapshot).toBeNull()
  expect(result.current.currentDraftId).toBeNull()
  expect(result.current.termsChanged).toBe(true)
  expect(result.current.requestText).toBe('Add a page')
  await act(async () => { await result.current.saveDraft() })
  expect(result.current.draftError).toBe('errors.draftProofInvalid')
  expect(vi.mocked(fetch).mock.calls.filter(([url]) => url === '/api/analyze')).toHaveLength(1)
  expect(vi.mocked(fetch).mock.calls.some(([url]) => url === '/api/drafts')).toBe(false)
})
it('invalidates a fixed-price amount change', async () => {
  projects[0] = { ...projects[0], pricingModel: 'fixed', hourlyRate: null, fixedPrice: '5000.00' }
  const { result } = await setup()
  await act(async () => { await result.current.updateProject('p1', { ...input(), pricingModel: 'fixed', hourlyRate: '', fixedPrice: '6000' }) })
  expect(result.current.termsChanged).toBe(true)
})
it.each([{ name: 'Renamed' }, { clientName: 'New client' }, { hourlyRate: '100' }])('keeps temporary analysis for presentation or equivalent numeric changes: %j', async changed => {
  const { result } = await setup()
  const snapshot = result.current.projectSnapshot
  await act(async () => { await result.current.updateProject('p1', { ...input(), ...changed }) })
  expect(result.current.status).toBe('result')
  expect(result.current.termsChanged).toBe(false)
  expect(result.current.projectSnapshot).toEqual(snapshot)
  await act(async () => { await result.current.saveDraft() })
  const post = vi.mocked(fetch).mock.calls.find(([url, init]) => url === '/api/drafts' && init?.method === 'POST')
  expect(JSON.parse(String(post?.[1]?.body)).proof).toBe('signed-proof')
})
it('updates untouched unsaved document metadata without writing a saved draft', async () => {
  const { result } = await setup()
  await act(async () => { await result.current.updateProject('p1', { ...input(), name: 'Renamed', clientName: 'New persisted client' }) })
  expect(result.current.draftDocument?.changeOrder).toMatchObject({ projectName: 'Renamed', clientName: 'New persisted client' })
  expect(vi.mocked(fetch).mock.calls.some(([, init]) => init?.method === 'PUT')).toBe(false)
})
it('keeps the optional end date out of PATCH, clears temporary proof, and uses the new date on the next run', async () => {
  const { result } = await setup()
  await act(async () => { await result.current.updateProject('p1', input(), { clientName: 'Server client', clientEmail: '', endDate: '2027-01-01' }) })
  const patch = vi.mocked(fetch).mock.calls.find(([, init]) => init?.method === 'PATCH')
  expect(JSON.parse(String(patch?.[1]?.body))).not.toHaveProperty('endDate')
  expect(JSON.parse(localStorage.getItem('scg:project:u1:p1')!).endDate).toBe('2027-01-01')
  expect(result.current.draftDocument).toBeNull()
  expect(result.current.termsChanged).toBe(true)
  act(() => result.current.runCheck())
  await waitFor(() => expect(result.current.status).toBe('result'))
  const analyzes = vi.mocked(fetch).mock.calls.filter(([url]) => url === '/api/analyze')
  expect(JSON.parse(String(analyzes[1][1]?.body)).endDate).toBe('2027-01-01')
})
it('keeps a loaded persisted draft and its document unchanged after project and local end-date edits', async () => {
  const { result } = await setup(false)
  await act(async () => { await result.current.openDraft('d1') })
  const historical = structuredClone(result.current.draftDocument)
  const snapshot = structuredClone(result.current.projectSnapshot)
  await act(async () => { await result.current.updateProject('p1', { ...input(), scope: 'New scope', clientName: 'New client' }, { clientName: 'New client', clientEmail: '', endDate: '2028-01-01' }) })
  expect(result.current.currentDraftId).toBe('d1')
  expect(result.current.draftDocument).toEqual(historical)
  expect(result.current.projectSnapshot).toEqual(snapshot)
  expect(result.current.analysisProject?.clientName).toBe('Historical client')
  expect(result.current.analysisProject?.startDate).toBe(snapshot?.startDate)
  expect(result.current.projectSnapshot?.endDate).toBe('2026-12-01')
  expect(result.current.termsChanged).toBe(false)
  expect(vi.mocked(fetch).mock.calls.some(([, init]) => init?.method === 'PUT')).toBe(false)
})
it('initializes new documents using the server client rather than stale browser details', async () => {
  localStorage.setItem('scg:project:u1:p1', JSON.stringify({ clientName: 'Stale browser client', clientEmail: '', endDate: '' }))
  const { result } = await setup()
  expect(result.current.draftDocument?.changeOrder?.clientName).toBe('Server client')
})
it('does not restore obsolete localStorage analysis or persist history on a check', async () => {
  localStorage.setItem('scg:client-materials:active:u1', JSON.stringify({ projectId: 'p1', historyId: 'h1' }))
  const { result } = await setup(false)
  expect(result.current.result).toBeNull()
  act(() => result.current.setRequestText('Add a page'))
  act(() => result.current.runCheck())
  await waitFor(() => expect(result.current.status).toBe('result'))
  expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).includes('/history'))).toBe(false)
})
it('deletes an active saved draft project, removes deep links, and selects a valid replacement', async () => {
  const { result } = await setup(false)
  await act(async () => { await result.current.openDraft('d1') })
  expect(window.location.search).toContain('draft=d1')
  localStorage.setItem('scg:project:u1:p1', '{}')
  localStorage.setItem('scg:project:u1:p2', 'keep')
  await act(async () => { await result.current.deleteProject('p1') })
  expect(result.current.selectedProjectId).toBe('p2')
  expect(result.current.currentDraftId).toBeNull()
  expect(result.current.draftDocument).toBeNull()
  expect(result.current.projectSnapshot).toBeNull()
  expect(result.current.view).toBe('projects')
  expect(window.location.search).toBe('')
  expect(localStorage.getItem('scg:project:u1:p1')).toBeNull()
  expect(localStorage.getItem('scg:project:u1:p2')).toBe('keep')
})
it('clears temporary proof when deleting the final project', async () => {
  projects = [projects[0]]
  const { result } = await setup()
  await act(async () => { await result.current.deleteProject('p1') })
  expect(result.current.selectedProject).toBeNull()
  expect(result.current.projects).toEqual([])
  expect(result.current.view).toBe('projects')
  await act(async () => { await result.current.saveDraft() })
  expect(result.current.draftError).toBe('errors.draftProofInvalid')
})
it('preserves an unrelated active document when deleting another project', async () => {
  const { result } = await setup()
  const document = result.current.draftDocument
  await act(async () => { await result.current.deleteProject('p2') })
  expect(result.current.draftDocument).toEqual(document)
  expect(result.current.selectedProjectId).toBe('p1')
})
it('preserves state when deletion fails', async () => {
  const { result } = await setup()
  override = (_url, init) => init?.method === 'DELETE' ? Promise.resolve(Response.json({ error: 'errors.requestFailed' }, { status: 500 })) : null
  await act(async () => { await expect(result.current.deleteProject('p1')).rejects.toThrow() })
  expect(result.current.projects).toHaveLength(2)
  expect(result.current.result).not.toBeNull()
})
it('does not resurrect a deleted project when an analysis completes late', async () => {
  const { result } = await setup(false)
  let finish!: (response: Response) => void
  override = url => url === '/api/analyze' ? new Promise(resolve => { finish = resolve }) : null
  act(() => result.current.setRequestText('Add a page'))
  act(() => result.current.runCheck())
  await act(async () => { await result.current.deleteProject('p1') })
  await act(async () => { finish(Response.json({ result: analysisFixture, proof: 'stale', projectSnapshot: projectSnapshotFixture })) })
  expect(result.current.draftDocument).toBeNull()
  expect(result.current.selectedProjectId).toBe('p2')
})
it('does not resurrect a deleted draft through a pending server open', async () => {
  const { result } = await setup(false)
  let finish!: (response: Response) => void
  override = url => url === '/api/drafts/d1' ? new Promise(resolve => { finish = resolve }) : null
  const opening = result.current.openDraft('d1')
  await act(async () => { await result.current.deleteProject('p1') })
  await act(async () => { finish(Response.json({ draft: saved })); await opening })
  expect(result.current.currentDraftId).toBeNull()
  expect(result.current.view).toBe('projects')
})

it('preserves manually edited unsaved document presentation when project metadata changes', async () => {
  const { result } = await setup()
  act(() => result.current.updateChangeOrder({ ...result.current.draftDocument!.changeOrder!, clientName: 'Custom recipient', projectName: 'Custom title' }))
  await act(async () => { await result.current.updateProject('p1', { ...input(), name: 'Renamed', clientName: 'Changed client' }) })
  expect(result.current.draftDocument?.changeOrder).toMatchObject({ clientName: 'Custom recipient', projectName: 'Custom title' })
})
it('preserves a loaded legacy saved draft without inventing a current client or project snapshot', async () => {
  const { result } = await setup(false)
  override = url => url === '/api/drafts/d1' ? json({ draft: { ...saved, projectSnapshot: null } }) : null
  await act(async () => { await result.current.openDraft('d1') })
  await act(async () => { await result.current.updateProject('p1', { ...input(), clientName: 'Changed client' }) })
  expect(result.current.projectSnapshot).toBeNull()
  expect(result.current.analysisProject?.clientName).toBe(documentFixture.projectDetails.clientName)
  expect(result.current.draftDocument).toEqual(documentFixture)
})
it('does not allow a pending estimate to restore cleared temporary analysis after editing', async () => {
  const { result } = await setup()
  let finish!: (response: Response) => void
  override = url => url === '/api/change-orders/estimate' ? new Promise(resolve => { finish = resolve }) : null
  const pending = result.current.createEstimate('p1', 'Add a page')
  const failed = expect(pending).rejects.toThrow('stale_estimate')
  await act(async () => { await result.current.updateProject('p1', { ...input(), scope: 'Changed scope' }) })
  await act(async () => { finish(Response.json({ result: analysisFixture })); await failed })
  expect(result.current.draftDocument).toBeNull()
})
it('does not restore a deleted project draft when an in-flight save returns', async () => {
  const { result } = await setup()
  let finish!: (response: Response) => void
  override = (url, init) => url === '/api/drafts' && init?.method === 'POST' ? new Promise(resolve => { finish = resolve }) : null
  const pending = result.current.saveDraft()
  await act(async () => { await result.current.deleteProject('p1') })
  await act(async () => { finish(Response.json({ draft: saved, entry: { id: 'h1', draftId: 'd1' } })); await pending })
  expect(result.current.currentDraftId).toBeNull()
  expect(result.current.selectedProjectId).toBe('p2')
  expect(window.location.search).toBe('')
  expect(result.current.draftDocument).toBeNull()
})
