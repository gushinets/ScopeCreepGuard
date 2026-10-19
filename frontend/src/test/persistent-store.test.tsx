// @vitest-environment jsdom
import { act, cleanup, fireEvent, renderHook, screen, waitFor } from '@testing-library/react'
import { IntlProvider } from 'use-intl'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import en from '@/shared/i18n/messages/en.json'
import type { WorkingDraft } from '@/features/drafts/model/workflow-types'
import { commercialSignature } from '@/features/change-orders/model/commercial-signature'
import type { EditableDraft } from '@/shared/api/documents'
import { PersistentStoreProvider } from './workspace'
import { ResultPanel } from '@/features/analysis/result-panel'
import { SaveFeedback } from '@/features/drafts/save-feedback'
import { applyUserPatch } from '@/features/drafts/model/user-patch'
import { useStore } from './workspace'

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
        saved = { ...(body.patch ? applyUserPatch(saved, body.patch) : { ...saved, ...body.changes }), revision: String(BigInt(saved.revision) + BigInt(1)) }
      }
      return Response.json({ draft: saved })
    }
    throw new Error('Unexpected request: ' + url)
  }))
})
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
const wrapper = ({ children }: { children: ReactNode }) => <IntlProvider locale="en" messages={en}><PersistentStoreProvider>{children}</PersistentStoreProvider></IntlProvider>

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

it('reopens the full original assessment while current agreement terms remain independent', async () => {
  analyzedDraft()
  Object.assign(saved.analysisRun!.resultSnapshot!, { verdict: 'out_of_scope', reasoning: 'A new page changes the agreed deliverables.', citations: ['Original scope'], suggestion: 'Approve the extra work first.', hasAdditionalWork: true, changeOrder: null, estimate: { estimatedHours: 8, additionalCost: '240.00', currency: 'USD' } })
  saved.draftDocument.changeOrder = { ...changeOrder('2027-02-01'), noAdditionalCharge: true }
  const original = structuredClone(saved.analysisRun)
  const withResult = ({ children }: { children: ReactNode }) => wrapper({ children: <>{children}<ResultPanel /></> })
  const hook = renderHook(() => useStore(), { wrapper: withResult })
  await screen.findByText('A new page changes the agreed deliverables.')
  expect(screen.getByText('$240.00')).toBeTruthy()
  await waitFor(() => expect(hook.result.current.draftDocument?.changeOrder).toMatchObject({ additionalCost: '333.00', currency: 'EUR', noAdditionalCharge: true }))
  act(() => hook.result.current.updateChangeOrder({ ...hook.result.current.draftDocument!.changeOrder!, estimatedHours: '', additionalCost: '', currency: '' }))
  await act(async () => hook.result.current.saveDraft())
  hook.unmount()
  const reopened = renderHook(() => useStore(), { wrapper: withResult })
  await screen.findByText('A new page changes the agreed deliverables.')
  for (const text of ['Original scope', 'Approve the extra work first.', '$240.00']) expect(screen.getByText(text)).toBeTruthy()
  await waitFor(() => expect(reopened.result.current.draftDocument?.changeOrder).toMatchObject({ estimatedHours: '', additionalCost: '', currency: '', noAdditionalCharge: true }))
  expect(saved.analysisRun).toEqual(original)
  expect(requests.some(path => path.endsWith('/agreements') || path.endsWith('/analyses'))).toBe(false)
})

it.each(['2027-02-01', ''])('restores current persisted estimate provenance for deadline %j, without forcing regeneration after another edit', async edited => {
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
  await waitFor(() => expect(screen.queryByRole('button', { name: en.result.prepareAgreement })).toBeNull())
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
  act(() => { result = hook.result.current.createEstimate(); void result.catch(() => {}) })
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

it.each([false, true])('passes only an intentional language override to a new analysis: override=%s', async override => {
  analyzedDraft()
  saved.draftDocument.reply.language = 'es'
  saved.draftDocument.languageSelection = { language: 'en', confidence: 0.4078, status: 'uncertain', selectedLanguage: 'es', override, version: 'test', requestHash: 'test' }
  let submitted: Record<string, unknown> | undefined
  const originalFetch = vi.mocked(fetch).getMockImplementation()!
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    if (String(input).endsWith('/analyses')) {
      submitted = JSON.parse(String(init?.body))
      return Response.json({ applied: true, draft: { ...saved, revision: '4' }, analysisRun: saved.analysisRun })
    }
    return originalFetch(input, init)
  })
  const hook = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  act(() => hook.result.current.runCheck())
  await waitFor(() => expect(submitted).toBeDefined())
  expect(submitted?.documentLanguage).toBe(override ? 'es' : undefined)
  expect(submitted?.locale).toBe('en')
})

it('refreshes automatically published History without replacing a newer saved request', async () => {
  analyzedDraft()
  saved.draftDocument.reply.text = 'Saved manual reply'
  const old = structuredClone(saved)
  const entry = { id: 'late-check', projectId: project.id, date: '2026-10-15', request: old.requestText, verdict: 'in_scope', summary: 'Earlier check' }
  let release!: (response: Response) => void
  let completed = false
  const delayed = new Promise<Response>(resolve => { release = resolve })
  const originalFetch = vi.mocked(fetch).getMockImplementation()!
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    if (String(input).endsWith('/analyses')) return delayed
    if (String(input) === '/api/v2/projects' && completed) return Response.json({ projects: [{ ...project, history: [entry] }] })
    return originalFetch(input, init)
  })
  const hook = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  act(() => hook.result.current.runCheck())
  await waitFor(() => expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).endsWith('/analyses'))).toBe(true))
  act(() => hook.result.current.setRequestText('Newer saved request'))
  await act(async () => hook.result.current.saveDraft())
  const newer = structuredClone(saved)
  completed = true
  await act(async () => { release(Response.json({ applied: false, draft: null, historyEntryId: entry.id, analysisRun: old.analysisRun })) })
  await waitFor(() => expect(hook.result.current.selectedProject?.history.map(item => item.id)).toContain(entry.id))
  expect(hook.result.current.requestText).toBe(newer.requestText)
  expect(hook.result.current.draftDocument?.reply.text).toBe('Saved manual reply')
  expect(hook.result.current.currentDraftId).toBe(old.id)
  expect(hook.result.current.currentHistoryEntryId).toBeNull()
  expect(hook.result.current.draftError).toBe('')
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
      if (scenario === 'pending edits') saved = structuredClone(response)
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
      await waitFor(() => expect(hook.result.current.requestText).toBe('Newer local request'))
      await waitFor(() => expect(hook.result.current.workflow?.status).toBe('saved'))
      if (scenario !== 'pending edits') expect(hook.result.current.draftError).toBe('')
      if (scenario === 'pending edits') {
        expect(saved.revision).toBe(String(BigInt(response.revision) + BigInt(1)))
        expect(hook.result.current.draftError).toBe('')
      }
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
  await act(async () => { await hook.result.current.workflow?.complete() })
  expect(hook.result.current.selectedProject?.history.map(entry => entry.id)).toEqual(['h1'])
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
  expect(bodies).toHaveLength(4)
  expect(bodies[1]).toEqual(bodies[0])
  expect(saved.requestText).toBe('Retry this exact edit')
})

it('renders persistent failure feedback and Retry, while continued typing stays local', async () => {
  const originalFetch = vi.mocked(fetch).getMockImplementation()!
  let fail = true
  const bodies: Record<string, unknown>[] = []
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    if (String(input) === '/api/v2/drafts/d1' && init?.method === 'PUT') {
      bodies.push(JSON.parse(String(init.body)))
      if (fail) return Response.json({ error: 'errors.requestFailed' }, { status: 503 })
    }
    return originalFetch(input, init)
  })
  const withFeedback = ({ children }: { children: ReactNode }) => wrapper({ children: <>{children}<SaveFeedback /></> })
  const hook = renderHook(() => useStore(), { wrapper: withFeedback })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  expect(screen.getByRole('status').textContent).toBe('Saved')
  vi.useFakeTimers()
  act(() => hook.result.current.setRequestText('Unsaved first'))
  expect(screen.getByRole('status').textContent).toBe(en.workflow.saving)
  await act(async () => { await vi.advanceTimersByTimeAsync(2750) })
  expect(bodies).toHaveLength(3)
  expect(screen.getByRole('alert').textContent).toBe(en.workflow.failed)
  act(() => hook.result.current.setRequestText('Newest local text'))
  await act(async () => { await vi.advanceTimersByTimeAsync(30_000) })
  expect(bodies).toHaveLength(3)
  expect(saved.requestText).toBe('Server-confirmed request')
  fail = false
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: en.workflow.retrySave })) })
  expect(saved.requestText).toBe('Newest local text')
  expect(bodies[3]).toEqual(bodies[0])
  expect(bodies[4].patch).toEqual({ requestText: 'Newest local text' })
  expect(bodies.every(body => !('changes' in body))).toBe(true)
  expect(screen.getByRole('status').textContent).toBe('Saved')
  vi.useRealTimers()
})

it('logs an autosave conflict without exposing its document content', async () => {
  const originalFetch = vi.mocked(fetch).getMockImplementation()!
  const log = vi.spyOn(console, 'error').mockImplementation(() => {})
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    if (String(input) === '/api/v2/drafts/d1' && init?.method === 'PUT') return Response.json({ error: 'errors.draftConflict' }, { status: 409 })
    return originalFetch(input, init)
  })
  try {
    const hook = renderHook(() => useStore(), { wrapper })
    await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
    act(() => hook.result.current.setRequestText('Do not log this request text'))
    await act(async () => { await expect(hook.result.current.workflow?.complete()).rejects.toThrow('errors.draftConflict') })
    await waitFor(() => expect(log).toHaveBeenCalled())
    const event = JSON.parse(String(log.mock.calls.find(([entry]) => String(entry).includes('draft_autosave_failed'))?.[0]))
    expect(event).toMatchObject({ event: 'draft_autosave_failed', draftId: 'd1', projectId: 'p1', revision: '3', error: 'errors.draftConflict' })
    expect(JSON.stringify(event)).not.toContain('Do not log this request text')
  } finally { log.mockRestore() }
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

it('does not discover or clear recovery belonging to a different user or Draft', async () => {
  const foreignUser = 'scg:unconfirmed:u2:d1:tab'
  const foreignDraft = 'scg:unconfirmed:u1:d2:tab'
  const buffer = { version: 1, draftId: 'd1', baseRevision: '3', changes: { requestText: 'Private foreign text', draftDocument: saved.draftDocument }, attempt: null, pendingPatch: { requestText: 'Private foreign text' } }
  localStorage.setItem(foreignUser, JSON.stringify(buffer))
  localStorage.setItem(foreignDraft, JSON.stringify({ ...buffer, draftId: 'd2' }))
  const hook = renderHook(() => useStore(), { wrapper })
  await waitFor(() => expect(hook.result.current.isLoadingProjects).toBe(false))
  expect(hook.result.current.workflow?.recovery).toBeNull()
  expect(hook.result.current.requestText).toBe('Server-confirmed request')
  act(() => hook.result.current.setRequestText('My own edit'))
  await act(async () => hook.result.current.saveDraft())
  expect(localStorage.getItem(foreignUser)).toContain('Private foreign text')
  expect(localStorage.getItem(foreignDraft)).toContain('Private foreign text')
})
