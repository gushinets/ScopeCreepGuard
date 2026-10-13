// @vitest-environment jsdom
import { act, cleanup, renderHook, screen, waitFor } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import en from '@/messages/en.json'
import type { WorkingDraft } from '@/lib/drafts/workflow-types'
import { commercialSignature } from '@/lib/change-order/commercial-signature'
import type { EditableDraft } from '@/lib/change-order/document'
import { PersistentStoreProvider } from './persistent-store'
import { ResultPanel } from './result-panel'
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
        saved = { ...saved, ...body.changes, revision: String(BigInt(saved.revision) + BigInt(1)) }
      }
      return Response.json({ draft: saved })
    }
    throw new Error('Unexpected request: ' + url)
  }))
})
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
const wrapper = ({ children }: { children: ReactNode }) => <NextIntlClientProvider locale="en" messages={en}><PersistentStoreProvider>{children}</PersistentStoreProvider></NextIntlClientProvider>

function analyzedDraft() {
  saved.lastAnalysisRunId = 'analysis'
  saved.analysisIsStale = false
  saved.analysisRun = { id: 'analysis', projectId: saved.projectId, sourceDraftId: saved.id, sourceDraftRevision: saved.revision,
    requestText: saved.requestText, projectSnapshot: { ...project, industry: 'Design', pricingModel: 'hourly', currency: 'EUR' },
    interfaceLocale: 'en', status: 'succeeded', finishedAt: saved.updatedAt,
    resultSnapshot: { verdict: 'in_scope', confidence: 90, summary: 'Summary', reasoning: 'Reason', citations: [], replies: saved.draftDocument.reply.generated,
      changeOrder: { description: '', timelineImpact: '', additionalCost: '', note: '' } } }
}

function changeOrder(endDate: string): EditableDraft {
  return { createdAt: '2026-10-12T00:00:00Z', language: 'en', projectName: project.name, description: 'Extra page',
    estimatedHours: '2', additionalCost: '333.00', currency: 'EUR', timelineImpact: 'Two days', rationale: '', note: 'Draft',
    providerName: '', clientName: '', clientEmail: '', endDate, additionalTerms: '', clientApproverName: '', approvalDate: '', noAdditionalCharge: false }
}

it.each(['2027-02-01', ''])('restores current persisted estimate provenance for deadline %j, but warns after another edit', async edited => {
  analyzedDraft()
  saved.analysisRun!.resultSnapshot!.verdict = 'out_of_scope'
  saved.analysisRun!.resultSnapshot!.estimateValid = true
  saved.analysisRun!.resultSnapshot!.commercialSignature = commercialSignature(saved.analysisRun!.projectSnapshot, project.endDate)
  saved.draftDocument.changeOrder = changeOrder(edited)
  const signature = commercialSignature(saved.analysisRun!.projectSnapshot, edited || project.endDate)
  Object.assign(saved.draftDocument, { estimate: { analysisRunId: 'estimate-run', sourceDraftRevision: '2', effectiveEndDate: edited || project.endDate, commercialSignature: signature, estimateValid: true } })
  const original = structuredClone(saved.analysisRun!.resultSnapshot)
  const withResult = ({ children }: { children: ReactNode }) => wrapper({ children: <>{children}<ResultPanel /></> })
  const hook = renderHook(() => useStore(), { wrapper: withResult })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  expect(screen.queryByRole('button', { name: en.drafts.save })).toBeNull()
  expect(hook.result.current.result?.commercialSignature).toBe(signature)
  expect(screen.queryByRole('button', { name: en.result.createChangeOrder })).toBeNull()
  hook.unmount()
  const reopened = renderHook(() => useStore(), { wrapper: withResult })
  await waitFor(() => expect(reopened.result.current.isLoadingProjects).toBe(false))
  expect(screen.queryByRole('button', { name: en.result.createChangeOrder })).toBeNull()
  act(() => reopened.result.current.updateChangeOrder({ ...reopened.result.current.draftDocument!.changeOrder!, endDate: '2028-03-01' }))
  await waitFor(() => expect(screen.queryByRole('button', { name: en.result.createChangeOrder })).not.toBeNull())
  expect(saved.analysisRun!.resultSnapshot).toEqual(original)
})

it.each([false, true])('flushes edited estimate inputs and only acknowledges a current response (competing save: %s)', async competing => {
  analyzedDraft()
  saved.analysisRun!.resultSnapshot!.verdict = 'out_of_scope'
  saved.analysisRun!.resultSnapshot!.estimateValid = true
  saved.analysisRun!.resultSnapshot!.commercialSignature = commercialSignature(saved.analysisRun!.projectSnapshot, project.endDate)
  saved.draftDocument.changeOrder = changeOrder(project.endDate)
  const original = structuredClone(saved.analysisRun)
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  let received = false
  const originalFetch = vi.mocked(fetch).getMockImplementation()!
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    if (String(input).endsWith('/estimate')) {
      const body = JSON.parse(String(init?.body))
      expect(body.expectedRevision).toBe(saved.revision)
      expect(saved.draftDocument.changeOrder?.endDate).toBe('2027-02-01')
      const draft = structuredClone(saved)
      draft.revision = String(BigInt(saved.revision) + BigInt(1))
      const signature = commercialSignature(draft.analysisRun!.projectSnapshot, '2027-02-01')
      const refreshed = { ...draft.analysisRun!.resultSnapshot!, commercialSignature: signature, estimateValid: true }
      Object.assign(draft.draftDocument, { estimate: { analysisRunId: 'estimate-run', sourceDraftRevision: saved.revision, effectiveEndDate: '2027-02-01', commercialSignature: signature, estimateValid: true } })
      saved = structuredClone(draft)
      received = true
      await gate
      return Response.json({ draft, analysisRun: { resultSnapshot: refreshed } })
    }
    return originalFetch(input, init)
  })
  const hook = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  act(() => hook.result.current.updateChangeOrder({ ...hook.result.current.draftDocument!.changeOrder!, endDate: '2027-02-01' }))
  let result!: Promise<unknown>
  act(() => { result = hook.result.current.createEstimate(project.id, saved.requestText); void result.catch(() => {}) })
  await waitFor(() => expect(received).toBe(true))
  if (competing) {
    act(() => hook.result.current.setRequestText('Newer saved request'))
    await act(async () => hook.result.current.saveDraft())
  }
  await act(async () => {
    release()
    if (competing) await expect(result).rejects.toThrow('errors.draftConflict')
    else await result
  })
  expect(hook.result.current.workflow?.status).toBe('saved')
  expect(saved.analysisRun).toEqual(original)
  if (competing) expect(hook.result.current.requestText).toBe('Newer saved request')
  else expect(hook.result.current.result?.commercialSignature).toBe(commercialSignature(saved.analysisRun!.projectSnapshot, '2027-02-01'))
})

it('shows the first successful analysis result after installing its response', async () => {
  const initial = structuredClone(saved)
  analyzedDraft()
  const response = { ...structuredClone(saved), revision: '4' }
  saved = initial
  const originalFetch = vi.mocked(fetch).getMockImplementation()!
  vi.mocked(fetch).mockImplementation(async (input, init) => String(input).endsWith('/analyses')
    ? Response.json({ applied: true, draft: response, analysisRun: response.analysisRun }) : originalFetch(input, init))
  const hook = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  act(() => hook.result.current.runCheck())
  await waitFor(() => expect(hook.result.current.status).toBe('result'))
})

for (const operation of ['regenerate', 'analysis'] as const) {
  it.each(['normal', 'saved edits', 'pending edits', 'navigation', 'unapplied after saved edits'] as const)(`${operation}: protects state with %s during a delayed response`, async scenario => {
    saved.revision = '9007199254740991'
    analyzedDraft()
    const initial = structuredClone(saved)
    const response = structuredClone(initial)
    response.revision = String(BigInt(initial.revision) + BigInt(1))
    response.draftDocument.reply.text = 'Generated reply'
    let release!: (value: Response) => void
    const delayed = new Promise<Response>(resolve => { release = resolve })
    const originalFetch = vi.mocked(fetch).getMockImplementation()!
    vi.mocked(fetch).mockImplementation(async (input, init) => {
      const url = String(input)
      if (url === `/api/v2/drafts/d1/${operation === 'analysis' ? 'analyses' : 'regenerate'}`) return delayed
      if (url === '/api/v2/drafts/d2') return Response.json({ draft: { ...initial, id: 'd2', projectId: 'p2', requestText: 'Other project' } })
      return originalFetch(input, init)
    })
    const hook = renderHook(() => useStore(), { wrapper })
    await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
    let running: Promise<void> | undefined
    act(() => {
      if (operation === 'analysis') hook.result.current.runCheck()
      else running = hook.result.current.workflow!.regenerate()
    })
    await waitFor(() => expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).endsWith(operation === 'analysis' ? '/analyses' : '/regenerate'))).toBe(true))
    if (scenario === 'saved edits' || scenario === 'pending edits' || scenario === 'unapplied after saved edits') {
      act(() => hook.result.current.setRequestText('Newer local request'))
      if (scenario !== 'pending edits') {
        saved = structuredClone(response)
        await act(async () => hook.result.current.saveDraft())
      }
    } else if (scenario === 'navigation') {
      await act(async () => hook.result.current.openDraft('d2'))
    }
    await act(async () => {
      release(Response.json(operation === 'analysis' ? { applied: scenario !== 'unapplied after saved edits', draft: scenario === 'unapplied after saved edits' ? null : response, analysisRun: response.analysisRun } : { draft: response }))
      await running
    })
    if (scenario === 'normal') {
      await waitFor(() => expect(hook.result.current.draftDocument?.reply.text).toBe('Generated reply'))
      expect(hook.result.current.workflow?.status).toBe('saved')
    } else if (scenario === 'navigation') {
      expect(hook.result.current.currentDraftId).toBe('d2')
      expect(hook.result.current.requestText).toBe('Other project')
    } else {
      expect(hook.result.current.requestText).toBe('Newer local request')
      expect(hook.result.current.workflow?.status).toBe(scenario === 'pending edits' ? 'conflict' : 'saved')
      if (scenario !== 'pending edits') expect(hook.result.current.draftError).toBe('')
    }
  })
}

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

it('autosaves edits before navigation without creating History', async () => {
  const hook = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  expect(hook.result.current.requestText).toBe('Server-confirmed request')
  expect(hook.result.current.currentDraftId).toBe('d1')
  vi.useFakeTimers()
  try {
    act(() => hook.result.current.setRequestText('Edited request'))
    await act(async () => { await vi.advanceTimersByTimeAsync(750) })
  } finally { vi.useRealTimers() }
  expect(saved.requestText).toBe('Edited request')
  expect(hook.result.current.workflow?.status).toBe('saved')
  expect(requests.some(path => path.endsWith('/history'))).toBe(false)
  hook.unmount()
  const reopened = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(reopened.result.current.requestText).toBe('Edited request'))
})

it('completes the persisted check after flushing and keeps the Draft editable', async () => {
  const originalFetch = vi.mocked(fetch).getMockImplementation()!
  let historyRequested = false
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    if (String(input) === '/api/v2/drafts/d1/history') {
      historyRequested = true
      expect(saved.requestText).toBe('Ready to complete')
      return Response.json({ entry: { id: 'h1', projectId: 'p1', request: saved.requestText, date: '2026-10-12', verdict: 'in_scope', summary: 'Complete' } })
    }
    return originalFetch(input, init)
  })
  const hook = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  act(() => hook.result.current.setRequestText('Ready to complete'))
  await act(async () => { await hook.result.current.workflow?.complete() })
  expect(historyRequested).toBe(true)
  expect(hook.result.current.currentHistoryEntryId).toBe('h1')
  expect(hook.result.current.currentDraftId).toBe('d1')
  act(() => hook.result.current.setRequestText('Still editable'))
  expect(hook.result.current.requestText).toBe('Still editable')
  expect(hook.result.current.workflow?.status).toBe('dirty')
})

it('retries the failed autosave payload without adding an empty edit', async () => {
  const originalFetch = vi.mocked(fetch).getMockImplementation()!
  const bodies: unknown[] = []
  let fail = true
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    if (String(input) === '/api/v2/drafts/d1' && init?.method === 'PUT') {
      bodies.push(JSON.parse(String(init.body)))
      if (fail) throw new Error('offline')
    }
    return originalFetch(input, init)
  })
  const hook = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  act(() => hook.result.current.setRequestText('Retry this exact edit'))
  await act(async () => { await expect(hook.result.current.workflow?.complete()).rejects.toThrow('errors.requestFailed') })
  expect(hook.result.current.workflow?.status).toBe('failed')
  fail = false
  await act(async () => { await hook.result.current.workflow?.retrySave() })
  expect(bodies).toHaveLength(2)
  expect(bodies[1]).toEqual(bodies[0])
  expect(saved.requestText).toBe('Retry this exact edit')
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
