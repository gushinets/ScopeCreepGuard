// @vitest-environment jsdom
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import en from '@/messages/en.json'
import type { WorkingDraft } from '@/lib/drafts/workflow-types'
import { PersistentStoreProvider } from './persistent-store'
import { useStore } from './store'

const router = { replace: vi.fn() }
vi.mock('next/navigation', () => ({ useRouter: () => router }))
const project = { id: 'p1', name: 'Server project', clientName: 'Server client', clientEmail: 'server@example.test', endDate: '2026-12-01', industry: 'Design', scope: 'Original scope', startDate: '2026-01-01', pricingModel: 'hourly', currency: 'EUR', hourlyRate: '100.00', fixedPrice: null, history: [] }
let saved: WorkingDraft
let requests: string[]
beforeEach(() => {
  requests = []
  localStorage.clear()
  window.history.replaceState({}, '', '/')
  saved = { id: 'd1', projectId: 'p1', revision: '3', requestText: 'Server-confirmed request', lastAnalysisRunId: null, analysisIsStale: true, draftDocument: { version: 2, reply: { text: '', tone: 'neutral', language: 'en', generated: { warm: '', neutral: '', firm: '' } }, changeOrder: null }, analysisRun: null, createdAt: '2026-10-12T00:00:00Z', updatedAt: '2026-10-12T00:00:00Z' }
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    requests.push(url)
    if (url === '/api/auth/me') return Response.json({ user: { id: 'u1', email: 'owner@example.test' } })
    if (url === '/api/v2/projects') return Response.json({ projects: [project] })
    if (url === '/api/v2/projects/p1/draft' || url === '/api/v2/drafts/d1') {
      if (init?.method === 'PUT') {
        const body = JSON.parse(String(init.body))
        saved = { ...saved, ...body.changes, revision: String(Number(saved.revision) + 1) }
      }
      return Response.json({ draft: saved })
    }
    throw new Error('Unexpected request: ' + url)
  }))
})
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
const wrapper = ({ children }: { children: ReactNode }) => <NextIntlClientProvider locale="en" messages={en}><PersistentStoreProvider>{children}</PersistentStoreProvider></NextIntlClientProvider>

it('does not create another project when opening its confirmed Draft temporarily fails', async () => {
  const originalFetch = vi.mocked(fetch).getMockImplementation()!
  let creations = 0
  let failOpen = true
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = String(input)
    if (url === '/api/v2/projects' && init?.method === 'POST') {
      creations += 1
      return Response.json({ project: { ...project, id: 'p2' } })
    }
    if (url === '/api/v2/projects/p2/draft') {
      if (failOpen) throw new Error('temporary network failure')
      return Response.json({ draft: { ...saved, id: 'd2', projectId: 'p2' } })
    }
    return originalFetch(input, init)
  })
  const hook = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  const input = { name: 'New project', industry: 'Design' as const, scope: 'Five pages', startDate: '2026-01-01', pricingModel: 'hourly' as const, currency: 'EUR' as const, hourlyRate: '100', fixedPrice: '' }
  await act(async () => { await expect(hook.result.current.createProject(input)).rejects.toThrow() })
  failOpen = false
  await act(async () => { await hook.result.current.createProject(input) })
  expect(creations).toBe(1)
  expect(hook.result.current.currentDraftId).toBe('d2')
})

it('opens server-confirmed state and saves before navigation without creating History', async () => {
  const hook = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  expect(hook.result.current.requestText).toBe('Server-confirmed request')
  expect(hook.result.current.currentDraftId).toBe('d1')
  act(() => hook.result.current.setRequestText('Edited request'))
  await act(async () => hook.result.current.saveDraft())
  expect(saved.requestText).toBe('Edited request')
  expect(hook.result.current.workflow?.status).toBe('saved')
  expect(requests.some(path => path.endsWith('/history'))).toBe(false)
  hook.unmount()
  const reopened = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(reopened.result.current.requestText).toBe('Edited request'))
})

it('offers recovery without automatically replacing the saved request', async () => {
  const sourceKey = 'scg:unconfirmed:u1:d1:other-tab'
  localStorage.setItem(sourceKey, JSON.stringify({ version: 1, draftId: 'd1', baseRevision: '3', changes: { requestText: 'Unconfirmed text', draftDocument: saved.draftDocument }, attempt: null }))
  const hook = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  expect(hook.result.current.workflow?.recovery).not.toBeNull()
  expect(hook.result.current.requestText).toBe('Server-confirmed request')
  expect(saved.requestText).toBe('Server-confirmed request')
  act(() => hook.result.current.workflow?.acceptRecovery())
  expect(localStorage.getItem(sourceKey)).toBeNull()
  expect(hook.result.current.requestText).toBe('Unconfirmed text')
  expect(saved.requestText).toBe('Server-confirmed request')
  await act(async () => hook.result.current.saveDraft())
  expect(saved.requestText).toBe('Unconfirmed text')
})
