'use client'

import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import { WorkflowOperations } from '@/lib/drafts/operations'
import { DraftAutosave, parseRecoveryBuffer, type RecoveryBuffer } from '@/lib/drafts/autosave'
import { WorkflowApiError, workflowApi } from '@/lib/drafts/workflow-client'
import type { ArchivedCheck, WorkingDraft, WorkingRevision } from '@/lib/drafts/workflow-types'
import { ERROR_CODES, type ErrorCode } from '@/lib/api/errors'
import type { DraftDocument, DraftListItem } from '@/lib/drafts/types'
import type { AnalysisResult, Project } from '@/lib/types'
import { StoreContext, type AnalysisStatus, type NewProjectInput, type StoreValue, type View } from './store'

type PersistentProject = Project & { clientEmail?: string | null; endDate?: string | null; archivedAt?: string | null }
const errorCode = (error: unknown) => error instanceof WorkflowApiError ? error.code : ERROR_CODES.requestFailed

export function PersistentStoreProvider({ children }: { children: ReactNode }) {
  const router = useRouter()
  const locale = useLocale()
  const t = useTranslations()
  const [user, setUser] = useState<{ id: string; email: string } | null>(null)
  const [projects, setProjects] = useState<PersistentProject[]>([])
  const [selectedProjectId, setProjectId] = useState<string | null>(null)
  const [view, changeView] = useState<View>('check')
  const [loading, setLoading] = useState(true)
  const [projectError, setProjectError] = useState<ErrorCode | ''>('')
  const [draftError, setDraftError] = useState<ErrorCode | ''>('')
  const [analysisError, setAnalysisError] = useState<ErrorCode | ''>('')
  const [status, setStatus] = useState<AnalysisStatus>('idle')
  const [snapshot, setSnapshot] = useState<WorkingDraft | null>(null)
  const [saveStatus, setSaveStatus] = useState<import('@/lib/drafts/autosave').SaveStatus>('saved')
  const [recovery, setRecovery] = useState<RecoveryBuffer | null>(null)
  const [historyId, setHistoryId] = useState<string | null>(null)
  const [legacyRevision, setLegacyRevision] = useState<WorkingRevision | null>(null)
  const operations = useRef(new WorkflowOperations((path, body, method) => workflowApi(path, body, method)))
  const confirmedProjectActions = useRef(new Map<string, PersistentProject>())
  const controller = useRef<DraftAutosave | null>(null)
  const reviewedConflict = useRef<WorkingDraft | null>(null)
  const owner = useRef<string>('')
  const navigation = useRef(0)
  const tab = useRef('')
  const recoverySource = useRef('')
  const reportedSaveIssue = useRef('')
  const recoveryKey = useCallback((id: string) => {
    if (!tab.current) {
      try { tab.current = sessionStorage.getItem('scg:recovery-tab') ?? crypto.randomUUID(); sessionStorage.setItem('scg:recovery-tab', tab.current) }
      catch { tab.current = crypto.randomUUID() }
    }
    return `scg:unconfirmed:${owner.current}:${id}:${tab.current}`
  }, [])

  const syncDraftUrl = useCallback((id: string | null) => {
    const url = new URL(window.location.href)
    if (id) url.searchParams.set('draft', id)
    else url.searchParams.delete('draft')
    window.history.replaceState(window.history.state, '', url)
  }, [])

  const install = useCallback((draft: WorkingDraft | null, legacyLink?: string) => {
    controller.current?.dispose()
    setLegacyRevision(null)
    reviewedConflict.current = null
    if (!draft) {
      controller.current = null
      setSnapshot(null); setProjectId(null); setStatus('idle'); setSaveStatus('saved')
      setHistoryId(null); setRecovery(null); setDraftError(''); setAnalysisError('')
      syncDraftUrl(null)
      return
    }
    const next = new DraftAutosave(draft, async body => (await workflowApi<{ draft: WorkingDraft }>(`drafts/${draft.id}`, body, 'PUT')).draft, () => {
      if (controller.current !== next) return
      setSnapshot({ ...next.local })
      setSaveStatus(next.status)
      setDraftError(next.error ? errorCode(next.error) : '')
      if (next.status === 'conflict' || next.status === 'failed') {
        const event = `draft_autosave_${next.status}`
        const issue = `${event}:${next.confirmed.id}:${next.confirmed.revision}`
        if (reportedSaveIssue.current !== issue) {
          reportedSaveIssue.current = issue
          console.error(JSON.stringify({ event, draftId: next.confirmed.id, projectId: next.confirmed.projectId, revision: next.confirmed.revision, error: next.error ? errorCode(next.error) : null }))
        }
      } else reportedSaveIssue.current = ''
    }, recoveryKey(draft.id))
    controller.current = next
    setSnapshot(draft)
    setSaveStatus('saved')
    setProjectId(draft.projectId)
    setStatus(draft.analysisRun?.resultSnapshot ? 'result' : 'idle')
    setHistoryId(null)
    setDraftError('')
    setAnalysisError('')
    syncDraftUrl(legacyLink ?? draft.id)
    try {
      const prefix = `scg:unconfirmed:${owner.current}:${draft.id}`
      const candidates = [recoveryKey(draft.id), ...Object.keys(localStorage).filter(key => key === prefix || key.startsWith(prefix + ':'))]
      recoverySource.current = candidates.find(key => localStorage.getItem(key)) ?? ''
      const raw = JSON.parse(localStorage.getItem(recoverySource.current) ?? 'null') as RecoveryBuffer | null
      const buffer = parseRecoveryBuffer(raw, draft.id)
      setRecovery(buffer)
      if (buffer) console.error(JSON.stringify({ event: 'draft_recovery_buffer_available', draftId: draft.id, projectId: draft.projectId, baseRevision: buffer.baseRevision, hasPendingOperation: !!buffer.attempt }))
    } catch { setRecovery(null) }
  }, [recoveryKey, syncDraftUrl])

  useEffect(() => {
    let active = true
    async function initialize() {
      try {
        const me = await fetch('/api/auth/me', { cache: 'no-store' })
        if (me.status === 401) { router.replace('/login'); return }
        if (!me.ok) throw new Error('session unavailable')
        const identity = (await me.json()).user
        owner.current = identity.id
        operations.current.setOwner(identity.id)
        const loaded = await workflowApi<{ projects: PersistentProject[] }>('projects')
        if (!active) return
        setUser(identity)
        setProjects(loaded.projects)
        const draftId = new URLSearchParams(window.location.search).get('draft')
        const first = loaded.projects[0]
        if (draftId) {
          try {
            const data = await workflowApi<{ draft: WorkingDraft }>(`drafts/${encodeURIComponent(draftId)}`)
            if (active) install(data.draft)
          } catch (error) {
            if (!(error instanceof WorkflowApiError) || error.status !== 404) throw error
            const legacy = await workflowApi<{ revision: WorkingRevision & { projectId: string } }>(`legacy-drafts/${encodeURIComponent(draftId)}`)
            const current = await workflowApi<{ draft: WorkingDraft }>(`projects/${legacy.revision.projectId}/draft`)
            if (active) { install(current.draft, draftId); setLegacyRevision(legacy.revision) }
          }
        } else if (first) {
          const data = await workflowApi<{ draft: WorkingDraft }>(`projects/${first.id}/draft`)
          if (active) install(data.draft)
        } else if (active) install(null)
        const current = controller.current
        if (active && current) {
          const resumed = await operations.current.resume<{ draft?: WorkingDraft | null }>(`drafts/${current.confirmed.id}/`)
          if (active && controller.current === current && resumed.length) {
            const refreshed = await workflowApi<{ draft: WorkingDraft }>(`drafts/${current.confirmed.id}`)
            if (active && controller.current === current && current.status === 'saved') install(refreshed.draft)
          }
        }
      } catch (error) { if (active) setProjectError(errorCode(error)) }
      finally { if (active) setLoading(false) }
    }
    void initialize()
    const unload = (event: BeforeUnloadEvent) => {
      if (controller.current && controller.current.status !== 'saved') { event.preventDefault(); event.returnValue = '' }
    }
    window.addEventListener('beforeunload', unload)
    return () => { active = false; controller.current?.dispose(); window.removeEventListener('beforeunload', unload) }
  }, [install, router])

  const selectedProject = projects.find(project => project.id === selectedProjectId) ?? null
  const rawResult = snapshot?.analysisRun?.resultSnapshot ?? null
  // Compatibility projection for the existing editor; only v2 editable fields are saved.
  const result: AnalysisResult | null = rawResult && snapshot ? {
    ...rawResult, replies: snapshot.draftDocument.reply.generated,
    clientLanguage: snapshot.draftDocument.reply.language,
    commercialSignature: snapshot.draftDocument.estimate?.commercialSignature ?? rawResult.commercialSignature,
    estimateValid: snapshot.draftDocument.estimate?.estimateValid ?? rawResult.estimateValid,
  } : null
  const analysisProject = selectedProject && snapshot?.analysisRun ? { ...selectedProject, ...snapshot.analysisRun.projectSnapshot, id: selectedProject.id, history: selectedProject.history } : selectedProject
  const draftDocument: DraftDocument | null = snapshot && result ? {
    version: 1, result, clientMaterials: null, changeOrder: snapshot.draftDocument.changeOrder,
    reply: snapshot.draftDocument.reply,
    languageSelection: snapshot.draftDocument.languageSelection,
    projectDetails: { clientName: selectedProject?.clientName ?? '', clientEmail: selectedProject?.clientEmail ?? '', endDate: selectedProject?.endDate ?? '' },
  } : null

  async function flush() {
    if (!controller.current) throw new Error('No Draft')
    return controller.current.flush()
  }
  function report(error: unknown) { setDraftError(errorCode(error)) }
  async function switchProject(id: string, destination: 'check' | 'edit_project' = 'check') {
    const run = ++navigation.current
    try {
      if (controller.current) await flush()
      const data = await workflowApi<{ draft: WorkingDraft }>(`projects/${id}/draft`)
      if (run !== navigation.current) return
      install(data.draft)
      changeView(destination)
    } catch (error) { if (run === navigation.current) report(error) }
  }
  function setRequestText(text: string) { controller.current?.edit({ requestText: text }) }
  async function setView(next: View) {
    try { if (controller.current) await flush(); changeView(next) } catch (error) { report(error) }
  }
  async function createProject(input: NewProjectInput) {
    const run = ++navigation.current
    if (controller.current) await flush()
    const parameters = { ...input, clientEmail: input.clientEmail || null, endDate: input.endDate || null }
    const signature = JSON.stringify(['create', parameters])
    const project = confirmedProjectActions.current.get(signature) ?? (await operations.current.run<{ project: PersistentProject }>('projects', parameters)).project
    confirmedProjectActions.current.set(signature, project)
    setProjects(current => [project, ...current.filter(item => item.id !== project.id)])
    const saved = await workflowApi<{ draft: WorkingDraft }>(`projects/${project.id}/draft`)
    if (run === navigation.current) { install(saved.draft); changeView('check') }
    confirmedProjectActions.current.delete(signature)
    return project
  }
  async function updateProject(id: string, input: NewProjectInput, details?: { clientName: string; clientEmail: string; endDate: string }) {
    const run = navigation.current
    const saved = await flush()
    const parameters = { ...input, clientName: details?.clientName ?? input.clientName, clientEmail: details?.clientEmail || null, endDate: details?.endDate || null, expectedRevision: saved.revision }
    const signature = JSON.stringify(['update', id, parameters])
    const updated = confirmedProjectActions.current.get(signature) ?? (await operations.current.run<{ project: PersistentProject }>(`projects/${id}`, parameters, 'PATCH')).project
    confirmedProjectActions.current.set(signature, updated)
    setProjects(current => current.map(project => project.id === id ? updated : project))
    const refreshed = await workflowApi<{ draft: WorkingDraft }>(`projects/${id}/draft`)
    if (run === navigation.current) { install(refreshed.draft); changeView('check') }
    confirmedProjectActions.current.delete(signature)
    return updated
  }
  async function deleteProject(id: string) {
    const run = ++navigation.current
    const current = controller.current
    if (controller.current) await flush()
    await workflowApi(`projects/${id}`, undefined, 'DELETE')
    const remaining = projects.filter(project => project.id !== id)
    setProjects(previous => previous.filter(project => project.id !== id))
    if (run !== navigation.current || current !== controller.current) return
    if (selectedProjectId === id) {
      const replacement = remaining[0] ? (await workflowApi<{ draft: WorkingDraft }>(`projects/${remaining[0].id}/draft`)).draft : null
      if (run !== navigation.current || current !== controller.current) return
      install(replacement)
    }
    changeView('projects')
  }
  function applyOperationResponse(current: DraftAutosave, edits: symbol, response: WorkingDraft, sourceRevision: string) {
    if (BigInt(response.revision) <= BigInt(current.confirmed.revision)) return false
    if (current.editToken !== edits || current.status !== 'saved') {
      if (current.editToken !== edits && current.rebaseOperationResponse(response, sourceRevision)) return true
      current.markConflict(new WorkflowApiError(ERROR_CODES.draftConflict, 409))
      return false
    }
    install(response)
    return true
  }
  async function applyAction(action: (saved: WorkingDraft) => Promise<WorkingDraft>) {
    const current = controller.current!
    const run = navigation.current
    const saved = await flush()
    if (run !== navigation.current || controller.current !== current) return false
    const edits = current.editToken
    const response = await action(saved)
    if (run !== navigation.current || controller.current !== current) return false
    return applyOperationResponse(current, edits, response, saved.revision)
  }
  async function runAnalysis() {
    const current = controller.current
    const run = navigation.current
    setAnalysisError('')
    try {
      const saved = await flush()
      if (!current || run !== navigation.current || current !== controller.current) return
      const edits = current.editToken
      setStatus('loading')
      const response = await operations.current.run<{ draft: WorkingDraft | null; analysisRun: WorkingDraft['analysisRun']; applied: boolean; historyEntryId?: string }>(`drafts/${saved.id}/analyses`, { expectedRevision: saved.revision, locale: locale === 'ru' ? 'ru' : 'en', ...(saved.draftDocument.languageSelection?.override ? { documentLanguage: saved.draftDocument.reply.language } : {}) })
      if (run !== navigation.current || current !== controller.current) return
      let applied = false
      if (!response.applied || !response.draft) {
        if (BigInt(current.confirmed.revision) <= BigInt(saved.revision)) current.markConflict(new WorkflowApiError(ERROR_CODES.draftConflict, 409))
      } else applied = applyOperationResponse(current, edits, response.draft, saved.revision)
      if (applied) {
        if (response.historyEntryId) setHistoryId(response.historyEntryId)
        // install() has already set status for an unchanged Draft. A rebased
        // response keeps this controller and needs the status update here.
        if (controller.current === current) setStatus(current.local.analysisRun?.resultSnapshot ? 'result' : 'idle')
      } else setStatus(current.local.analysisRun?.resultSnapshot ? 'result' : 'idle')
      if (response.historyEntryId) {
        const active = controller.current
        const refreshed = await workflowApi<{ projects: PersistentProject[] }>('projects')
        if (run === navigation.current && active === controller.current) setProjects(refreshed.projects)
      }
    } catch (error) {
      if (run !== navigation.current || current !== controller.current) return
      setAnalysisError(errorCode(error)); setStatus('error')
    }
  }
  async function retrySave() { await flush() }
  async function complete() {
    const saved = await flush()
    const response = await operations.current.run<{ entry: ArchivedCheck }>(`drafts/${saved.id}/history`, { expectedRevision: saved.revision })
    setHistoryId(response.entry.id)
    setProjects(current => current.map(project => project.id === saved.projectId ? { ...project, history: [response.entry, ...project.history.filter(entry => entry.id !== response.entry.id)] } : project))
  }
  async function regenerate() { await applyAction(async saved => (await operations.current.run<{ draft: WorkingDraft }>(`drafts/${saved.id}/regenerate`, { expectedRevision: saved.revision })).draft) }
  async function changeClientLanguage(language: string) {
    const document = controller.current?.local.draftDocument
    const order = document?.changeOrder
    const edited = document && (document.reply.text !== document.reply.generated[document.reply.tone] ||
      order && (['description', 'timelineImpact', 'rationale', 'note'] as const).some(field => order[field] !== order.aiValues?.[field]) || !!order?.additionalTerms)
    if (edited && !window.confirm(t('result.confirmClientLanguage'))) return true
    await applyAction(async saved => (await operations.current.run<{ draft: WorkingDraft }>(`drafts/${saved.id}/translate`, { expectedRevision: saved.revision, language })).draft)
    return false
  }
  async function reset() { try { await applyAction(async saved => (await operations.current.run<{ draft: WorkingDraft }>(`drafts/${saved.id}/clear`, { expectedRevision: saved.revision })).draft) } catch (error) { report(error) } }
  async function openDraft(id: string) {
    const run = ++navigation.current
    if (controller.current) await flush()
    const data = await workflowApi<{ draft: WorkingDraft }>(`drafts/${id}`)
    if (run === navigation.current) { install(data.draft); changeView('check') }
  }
  async function listDrafts(): Promise<DraftListItem[]> {
    const current = await workflowApi<{ projects: PersistentProject[] }>('projects')
    return Promise.all(current.projects.map(async project => {
      const { draft } = await workflowApi<{ draft: WorkingDraft }>(`projects/${project.id}/draft`)
      return { id: draft.id, projectName: project.name, requestPreview: draft.requestText.slice(0, 160), verdict: draft.analysisRun?.resultSnapshot?.verdict ?? null, createdAt: draft.createdAt, updatedAt: draft.updatedAt }
    }))
  }
  async function resolveConflict(keepLocal: boolean) {
    const current = controller.current
    if (!current) return
    try { await current.flush() } catch { /* The failed payload remains available for review. */ }
    const draft = keepLocal ? reviewedConflict.current : (await workflowApi<{ draft: WorkingDraft }>(`drafts/${current.confirmed.id}`)).draft
    if (!draft || draft.id !== current.confirmed.id) throw new Error('Review the server version first')
    current.resolve(draft, keepLocal)
    if (keepLocal) await current.flush()
    setSnapshot({ ...current.local }); setSaveStatus(current.status); setDraftError('')
  }
  async function downloadEvaluationsExport() {
    const response = await fetch('/api/evaluations/export', { cache: 'no-store' })
    if (!response.ok) throw new WorkflowApiError(ERROR_CODES.requestFailed, response.status)
    const url = URL.createObjectURL(await response.blob())
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'scope-creep-evaluations.jsonl'; anchor.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 10000)
  }
  const value: StoreValue = {
    user, projects, selectedProject, selectedProjectId, analysisProject,
    projectSnapshot: snapshot?.analysisRun ? { ...snapshot.analysisRun.projectSnapshot, version: 1, documentLanguage: snapshot.draftDocument.reply.language, endDate: snapshot.analysisRun.projectSnapshot.endDate ?? null } : null,
    view, requestText: snapshot?.requestText ?? '', analyzedRequest: snapshot?.analysisRun?.requestText ?? null,
    status, result, clientMaterials: null, draftDocument, currentDraftId: snapshot?.id ?? null,
    draftSessionId: snapshot?.id ?? '', isSavingDraft: saveStatus === 'saving', draftError,
    isDraftDirty: saveStatus !== 'saved', saveDraft: retrySave, openDraft, listDrafts,
    updateReply: reply => {
      const current = controller.current?.local.draftDocument
      if (current) controller.current?.edit({ draftDocument: { ...current, reply: { ...current.reply, ...reply } } }, current.reply.tone === reply.tone ? 'autosave' : 'tone_change', current.reply.tone !== reply.tone)
    },
    updateChangeOrder: changeOrder => {
      const current = controller.current?.local.draftDocument
      if (current) {
        const prior = current.changeOrder
        const structured = (['currency', 'noAdditionalCharge', 'endDate', 'approvalDate', 'estimatedHours', 'additionalCost', 'language'] as const).some(field => prior?.[field] !== changeOrder[field])
        controller.current?.edit({ draftDocument: { ...current, changeOrder } }, 'change_order_edit', structured)
      }
    },
    changeClientLanguage, currentHistoryEntryId: historyId, analysisError, isLoadingProjects: loading, projectError,
    termsChanged: !!snapshot?.analysisIsStale && !!result, deleteProject,
    setView: next => { void setView(next) }, selectProject: (id, destination) => { void switchProject(id, destination) },
    createProject, updateProject,
    createEstimate: async () => {
      let estimate: AnalysisResult | null = null
      const applied = await applyAction(async saved => {
        const response = await operations.current.run<{ draft: WorkingDraft | null; analysisRun: { resultSnapshot: AnalysisResult } }>(`drafts/${saved.id}/estimate`, { expectedRevision: saved.revision })
        if (!response.draft) throw new WorkflowApiError(ERROR_CODES.draftConflict, 409)
        estimate = response.analysisRun.resultSnapshot
        return response.draft
      })
      if (!applied || !estimate) throw new WorkflowApiError(ERROR_CODES.draftConflict, 409)
      return estimate
    },
    setRequestText, loadExample: setRequestText, runCheck: () => { void runAnalysis() }, reset: () => { void reset() },
    logout: async () => { if (controller.current) await flush(); const response = await fetch('/api/auth/logout', { method: 'POST' }); if (!response.ok) throw new Error('Logout failed'); router.replace('/login') },
    submitEvaluation: async feedback => { if (!snapshot?.lastAnalysisRunId) throw new Error('No analysis'); await workflowApi(`analyses/${snapshot.lastAnalysisRunId}/evaluation`, feedback) },
    downloadEvaluationsExport,
    workflow: {
      openHistory: async identifier => {
        if (!window.confirm(t('workflow.confirmReopen'))) return
        const saved = await flush()
        const run = navigation.current
        const restored = await operations.current.run<{ draft: WorkingDraft }>(`history/${identifier}/restore`, { expectedRevision: saved.revision })
        if (run === navigation.current) { install(restored.draft); setHistoryId(identifier); changeView('check') }
      },
      status: saveStatus, stale: snapshot?.analysisIsStale ?? true, recovery,
      acceptRecovery: () => {
        if (!recovery) return
        controller.current?.recover(recovery)
        try {
          const destination = recoveryKey(recovery.draftId)
          const transferred = parseRecoveryBuffer(JSON.parse(localStorage.getItem(destination) ?? 'null'), recovery.draftId)
          if (destination !== recoverySource.current && JSON.stringify(transferred?.changes) === JSON.stringify(recovery.changes)) localStorage.removeItem(recoverySource.current)
        } catch { /* Keep the original buffer if durable recovery transfer was unavailable. */ }
        setRecovery(null)
      },
      discardRecovery: () => { localStorage.removeItem(recoverySource.current); setRecovery(null) },
      resolveConflict, complete, retrySave, regenerate,
      prepareAgreement: async () => {
        const applied = await applyAction(async saved => {
          if (saved.draftDocument.changeOrder) return saved
          const response = await operations.current.run<{ draft: WorkingDraft }>(`drafts/${saved.id}/agreement`, { expectedRevision: saved.revision })
          return response.draft
        })
        if (!applied) throw new WorkflowApiError(ERROR_CODES.draftConflict, 409)
      },
      compareConflict: async () => {
        const draft = controller.current ? (await workflowApi<{ draft: WorkingDraft }>(`drafts/${controller.current.confirmed.id}`)).draft : null
        reviewedConflict.current = draft
        return draft
      },
      legacyRevision, closeLegacy: () => { setLegacyRevision(null); syncDraftUrl(controller.current?.confirmed.id ?? null) },
      archivedProjects: async () => (await workflowApi<{ projects: PersistentProject[] }>('projects?archived=true')).projects,
      openArchived: async project => { setProjects(current => [...current.filter(item => item.id !== project.id), project]); await switchProject(project.id); changeView('history') },
      archived: !!selectedProject?.archivedAt,
    },
  }
  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
}
