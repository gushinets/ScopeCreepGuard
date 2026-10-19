import { useCallback, useEffect, useRef, useState } from 'react'
import { DraftAutosave, parseRecoveryBuffer, type RecoveryBuffer, type SaveStatus } from './model/autosave'
import { workflowApi, WorkflowApiError } from './model/workflow-client'
import type { WorkingDraft, WorkingRevision } from './model/workflow-types'
import type { ReplyDocument } from './model/types'
import type { EditableDraft } from '@/features/change-orders'
import { ERROR_CODES, type ErrorCode } from '@/shared/api/errors'
import { recoveryStorage, tabStorage } from '@/shared/storage/browser'

export const draftErrorCode = (failure: unknown) => failure instanceof WorkflowApiError ? failure.code : ERROR_CODES.requestFailed

/** The sole editable Draft representation. Server resources and operations live outside this hook. */
export function useDraftEditor(owner: string, onDraftUrl: (id: string | null) => void) {
  const [snapshot, setSnapshot] = useState<WorkingDraft | null>(null)
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('saved')
  const [draftError, setDraftError] = useState<ErrorCode | ''>('')
  const [recovery, setRecovery] = useState<RecoveryBuffer | null>(null)
  const [legacyRevision, setLegacyRevision] = useState<WorkingRevision | null>(null)
  const [historyId, setHistoryId] = useState<string | null>(null)
  const controller = useRef<DraftAutosave | null>(null)
  const reviewedConflict = useRef<WorkingDraft | null>(null)
  const tab = useRef('')
  const recoverySource = useRef('')
  const reportedSaveIssue = useRef('')
  const navigation = useRef(0)
  const recoveryKey = useCallback((id: string) => {
    if (!tab.current) {
      try { tab.current = tabStorage.get('scg:recovery-tab') ?? crypto.randomUUID(); tabStorage.set('scg:recovery-tab', tab.current) }
      catch { tab.current = crypto.randomUUID() }
    }
    return `scg:unconfirmed:${owner}:${id}:${tab.current}`
  }, [owner])
  const install = useCallback((draft: WorkingDraft | null, legacyLink?: string) => {
    controller.current?.dispose()
    setLegacyRevision(null); reviewedConflict.current = null
    setHistoryId(null); setRecovery(null); setDraftError('')
    if (!draft) {
      controller.current = null; setSnapshot(null); setSaveStatus('saved'); onDraftUrl(null); return
    }
    const next: DraftAutosave = new DraftAutosave(draft, async body => {
      const payload = body.patch ? { expectedRevision: body.expectedRevision, operationId: body.operationId, patch: body.patch, reason: body.reason } : body
      return (await workflowApi<{ draft: WorkingDraft }>(`drafts/${draft.id}`, payload, 'PUT', AbortSignal.timeout(15_000))).draft
    }, () => {
      if (controller.current !== next) return
      setSnapshot({ ...next.local }); setSaveStatus(next.status)
      setDraftError(next.error ? draftErrorCode(next.error) : '')
      if (next.status === 'conflict' || next.status === 'failed') {
        const event = `draft_autosave_${next.status}`
        const issue = `${event}:${next.confirmed.id}:${next.confirmed.revision}`
        if (reportedSaveIssue.current !== issue) {
          reportedSaveIssue.current = issue
          console.error(JSON.stringify({ event, draftId: next.confirmed.id, projectId: next.confirmed.projectId, revision: next.confirmed.revision, error: next.error ? draftErrorCode(next.error) : null }))
        }
      } else reportedSaveIssue.current = ''
    }, recoveryKey(draft.id))
    controller.current = next; setSnapshot(draft); setSaveStatus('saved'); onDraftUrl(legacyLink ?? draft.id)
    try {
      const prefix = `scg:unconfirmed:${owner}:${draft.id}`
      const candidates = [recoveryKey(draft.id), ...recoveryStorage.keys().filter(key => key === prefix || key.startsWith(prefix + ':'))]
      recoverySource.current = candidates.find(key => recoveryStorage.get(key)) ?? ''
      const buffer = parseRecoveryBuffer(JSON.parse(recoveryStorage.get(recoverySource.current) ?? 'null'), draft.id)
      setRecovery(buffer)
      if (buffer) console.error(JSON.stringify({ event: 'draft_recovery_buffer_available', draftId: draft.id, projectId: draft.projectId, baseRevision: buffer.baseRevision, hasPendingOperation: !!buffer.attempt }))
    } catch { setRecovery(null) }
  }, [owner, recoveryKey, onDraftUrl])

  useEffect(() => {
    const unload = (event: BeforeUnloadEvent) => {
      if (controller.current && controller.current.status !== 'saved') { event.preventDefault(); event.returnValue = '' }
    }
    window.addEventListener('beforeunload', unload)
    return () => { navigation.current++; controller.current?.dispose(); window.removeEventListener('beforeunload', unload) }
  }, [])
  async function flush() {
    if (!controller.current) throw new Error('No Draft')
    return controller.current.flush()
  }
  async function beforeNavigate() { if (controller.current) await controller.current.flush() }
  function report(failure: unknown) { setDraftError(draftErrorCode(failure)) }
  function applyOperationResponse(current: DraftAutosave, edits: symbol, response: WorkingDraft, sourceRevision: string) {
    if (BigInt(response.revision) <= BigInt(current.confirmed.revision)) return false
    if (current.editToken !== edits || current.status !== 'saved') {
      if (current.editToken !== edits && current.rebaseOperationResponse(response, sourceRevision)) return true
      current.markConflict(new WorkflowApiError(ERROR_CODES.draftConflict, 409)); return false
    }
    install(response); return true
  }
  async function applyAction(action: (saved: WorkingDraft) => Promise<WorkingDraft>) {
    const current = controller.current
    const run = navigation.current
    const saved = await flush()
    if (!current || run !== navigation.current || controller.current !== current) return false
    const edits = current.editToken
    const response = await action(saved)
    if (run !== navigation.current || controller.current !== current) return false
    return applyOperationResponse(current, edits, response, saved.revision)
  }
  async function compareConflict() {
    const draft = controller.current ? (await workflowApi<{ draft: WorkingDraft }>(`drafts/${controller.current.confirmed.id}`)).draft : null
    reviewedConflict.current = draft; return draft
  }
  async function resolveConflict(keepLocal: boolean) {
    const current = controller.current
    if (!current) return
    try { await current.flush() } catch { /* Keep failed payload for review. */ }
    const draft = keepLocal ? reviewedConflict.current : (await workflowApi<{ draft: WorkingDraft }>(`drafts/${current.confirmed.id}`)).draft
    if (!draft || draft.id !== current.confirmed.id) throw new Error('Review the server version first')
    current.resolve(draft, keepLocal)
    if (keepLocal) await current.flush()
    setSnapshot({ ...current.local }); setSaveStatus(current.status); setDraftError('')
  }
  function acceptRecovery() {
    if (!recovery) return
    controller.current?.recover(recovery)
    try {
      const destination = recoveryKey(recovery.draftId)
      const transferred = parseRecoveryBuffer(JSON.parse(recoveryStorage.get(destination) ?? 'null'), recovery.draftId)
      if (destination !== recoverySource.current && JSON.stringify(transferred?.changes) === JSON.stringify(recovery.changes)) recoveryStorage.remove(recoverySource.current)
    } catch { /* Keep original when durable transfer is unavailable. */ }
    setRecovery(null)
  }
  function updateReply(reply: ReplyDocument) {
    const current = controller.current?.local.draftDocument
    if (current) controller.current?.edit({ draftDocument: { ...current, reply: { ...current.reply, ...reply } } }, current.reply.tone === reply.tone ? 'autosave' : 'tone_change', current.reply.tone !== reply.tone)
  }
  function updateChangeOrder(changeOrder: EditableDraft) {
    const current = controller.current?.local.draftDocument
    if (!current) return
    const structured = (['currency', 'noAdditionalCharge', 'endDate', 'approvalDate', 'estimatedHours', 'additionalCost', 'language'] as const).some(field => current.changeOrder?.[field] !== changeOrder[field])
    controller.current?.edit({ draftDocument: { ...current, changeOrder } }, 'change_order_edit', structured)
  }
  return { snapshot, controller, navigation, install, flush, beforeNavigate, report, applyAction, applyOperationResponse,
    legacyRevision, setLegacyRevision, historyId, setHistoryId, saveStatus, draftError, recovery,
    compareConflict, resolveConflict, acceptRecovery, discardRecovery: () => { recoveryStorage.remove(recoverySource.current); setRecovery(null) },
    closeLegacy: () => { setLegacyRevision(null); onDraftUrl(controller.current?.confirmed.id ?? null) },
    setRequestText: (text: string) => controller.current?.edit({ requestText: text }), updateReply, updateChangeOrder }
}
export type DraftEditor = ReturnType<typeof useDraftEditor>
