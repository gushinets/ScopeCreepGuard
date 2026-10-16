// @vitest-environment jsdom
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import en from '@/messages/en.json'
import type { Project } from '@/lib/types'
import type { WorkingDraft } from '@/lib/drafts/workflow-types'
import { PersistentStoreProvider } from './persistent-store'
import { useStore } from './store'

const router = { replace: vi.fn() }
vi.mock('next/navigation', () => ({ useRouter: () => router }))
let projects: Project[]
let drafts: Map<string, WorkingDraft>
const input = { name: 'New project', industry: 'Design' as const, scope: 'Five pages', startDate: '2026-01-01', pricingModel: 'hourly' as const, currency: 'EUR' as const, hourlyRate: '100', fixedPrice: '' }
const wrapper = ({ children }: { children: ReactNode }) => <NextIntlClientProvider locale="en" messages={en}><PersistentStoreProvider>{children}</PersistentStoreProvider></NextIntlClientProvider>

beforeEach(() => {
  localStorage.clear()
  window.history.replaceState({ retained: true }, '', '/?keep=value&draft=d1#reply')
  projects = [1, 2, 3].map(number => ({ ...input, id: `p${number}`, name: `Project ${number}`, currency: 'EUR', industry: 'Design', pricingModel: 'hourly', fixedPrice: null, history: [] }))
  drafts = new Map(projects.map((project, index) => [`d${index + 1}`, {
    id: `d${index + 1}`, projectId: project.id, revision: '1', requestText: `Request ${index + 1}`, analysisIsStale: true, lastAnalysisRunId: null,
    draftDocument: { version: 2, reply: { text: '', tone: 'neutral', language: 'en', generated: { warm: '', neutral: '', firm: '' } }, changeOrder: null },
    analysisRun: null, createdAt: '2026-10-12T00:00:00Z', updatedAt: '2026-10-12T00:00:00Z',
  }]))
  vi.stubGlobal('fetch', vi.fn(async (request: RequestInfo | URL, init?: RequestInit) => {
    const url = String(request)
    if (url === '/api/auth/me') return Response.json({ user: { id: 'owner', email: 'owner@example.test' } })
    if (url === '/api/v2/projects') {
      if (init?.method === 'POST') {
        const project = { ...projects[0], id: 'p4', name: 'New project', history: [] }
        projects.push(project)
        drafts.set('d4', { ...structuredClone(drafts.get('d1')!), id: 'd4', projectId: 'p4' })
        return Response.json({ project })
      }
      return Response.json({ projects })
    }
    if (init?.method === 'DELETE') {
      projects = projects.filter(project => !url.endsWith(`/${project.id}`))
      return Response.json({ ok: true })
    }
    if (url.startsWith('/api/v2/drafts/')) {
      const draft = drafts.get(url.split('/').at(-1)!)
      return draft ? Response.json({ draft }) : Response.json({ error: 'errors.draftNotFound' }, { status: 404 })
    }
    if (url.startsWith('/api/v2/legacy-drafts/')) return Response.json({ revision: {
      id: 'legacy', projectId: 'p2', draftId: 'd2', revision: '1', reason: 'legacy_import', createdAt: '', stateSnapshot: { ...drafts.get('d2'), legacy: { id: 'legacy' } },
    } })
    const draft = [...drafts.values()].find(draft => url === `/api/v2/projects/${draft.projectId}/draft`)
    if (draft) return Response.json({ draft })
    throw new Error(`Unexpected request: ${url}`)
  }))
})
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

function expectUrl(id: string | null) {
  const url = new URL(window.location.href)
  expect(url.searchParams.get('draft')).toBe(id)
  expect(url.searchParams.get('keep')).toBe('value')
  expect(url.hash).toBe('#reply')
  expect(window.history.state).toEqual({ retained: true })
}

it.each(['list', 'project', 'creation', 'archival'] as const)('synchronizes %s activation and restores it on reload', async path => {
  const hook = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  if (path === 'list') await act(async () => hook.result.current.openDraft('d2'))
  if (path === 'project') { act(() => hook.result.current.selectProject('p2')); await waitFor(() => expect(hook.result.current.currentDraftId).toBe('d2')) }
  if (path === 'creation') await act(async () => { await hook.result.current.createProject(input) })
  if (path === 'archival') await act(async () => hook.result.current.deleteProject('p1'))
  const active = path === 'creation' ? 'd4' : 'd2'
  expect(hook.result.current.currentDraftId).toBe(active)
  expectUrl(active)
  hook.unmount()
  const reopened = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(reopened.result.current.isLoadingProjects).toBe(false))
  expect(reopened.result.current.currentDraftId).toBe(active)
  expectUrl(active)
})

it('removes only the Draft parameter after archiving the last project', async () => {
  projects = projects.slice(0, 1)
  const hook = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  await act(async () => hook.result.current.deleteProject('p1'))
  expect(hook.result.current.currentDraftId).toBeNull()
  expectUrl(null)
  hook.unmount()
  const reopened = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(reopened.result.current.isLoadingProjects).toBe(false))
  expect(reopened.result.current.currentDraftId).toBeNull()
  expectUrl(null)
})

it.each(['project', 'list', 'creation', 'archival'] as const)('leaves the active URL unchanged after failed %s navigation', async path => {
  const original = vi.mocked(fetch).getMockImplementation()!
  const blocked = path === 'list' ? '/api/v2/drafts/d2' : `/api/v2/projects/${path === 'creation' ? 'p4' : 'p2'}/draft`
  vi.mocked(fetch).mockImplementation(async (request, init) => String(request) === blocked
    ? Response.json({ error: 'errors.requestFailed' }, { status: 503 }) : original(request, init))
  const hook = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  if (path === 'project') {
    act(() => hook.result.current.selectProject('p2'))
    await waitFor(() => expect(hook.result.current.draftError).toBe('errors.requestFailed'))
  } else await act(async () => {
    const operation = path === 'list' ? hook.result.current.openDraft('d2') : path === 'creation' ? hook.result.current.createProject(input) : hook.result.current.deleteProject('p1')
    await expect(operation).rejects.toThrow('errors.requestFailed')
  })
  expect(hook.result.current.currentDraftId).toBe('d1')
  expectUrl('d1')
})

it.each(['project', 'creation', 'archival'] as const)('ignores superseded %s activation', async path => {
  const original = vi.mocked(fetch).getMockImplementation()!
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  let waiting = false
  const blocked = `/api/v2/projects/${path === 'creation' ? 'p4' : 'p2'}/draft`
  vi.mocked(fetch).mockImplementation(async (request, init) => {
    if (String(request) === blocked) { waiting = true; await gate }
    return original(request, init)
  })
  const hook = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  let pending: Promise<unknown> | undefined
  act(() => {
    if (path === 'project') hook.result.current.selectProject('p2')
    if (path === 'creation') pending = hook.result.current.createProject(input)
    if (path === 'archival') pending = hook.result.current.deleteProject('p1')
  })
  await waitFor(() => expect(waiting).toBe(true))
  await act(async () => hook.result.current.openDraft('d3'))
  await act(async () => { release(); await pending })
  expect(hook.result.current.currentDraftId).toBe('d3')
  expect(hook.result.current.view).toBe('check')
  expectUrl('d3')
})

it('keeps legacy snapshot links until explicitly closing the snapshot', async () => {
  window.history.replaceState(window.history.state, '', '/?keep=value&draft=legacy#reply')
  const hook = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  expect(hook.result.current.workflow?.legacyRevision?.id).toBe('legacy')
  expect(hook.result.current.currentDraftId).toBe('d2')
  expectUrl('legacy')
  hook.unmount()
  const reopened = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(reopened.result.current.workflow?.legacyRevision?.id).toBe('legacy'))
  act(() => reopened.result.current.workflow?.closeLegacy())
  expectUrl('d2')
})

it('viewing History does not activate another Draft or change its URL', async () => {
  const hook = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  act(() => hook.result.current.setView('history'))
  await waitFor(() => expect(hook.result.current.view).toBe('history'))
  expect(hook.result.current.currentDraftId).toBe('d1')
  expect(hook.result.current.requestText).toBe('Request 1')
  expectUrl('d1')
})
it('opens the selected project editor after asynchronous draft loading', async () => {
  const hook = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  act(() => hook.result.current.selectProject('p2', 'edit_project'))
  await waitFor(() => expect(hook.result.current.currentDraftId).toBe('d2'))
  expect(hook.result.current.view).toBe('edit_project')
  expectUrl('d2')
})
