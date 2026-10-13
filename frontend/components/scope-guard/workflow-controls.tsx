'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import type { WorkingRevision } from '@/lib/drafts/workflow-types'
import type { WorkingDraft } from '@/lib/drafts/workflow-types'
import { useStore } from './store'

const reasons = ['initial', 'autosave', 'manual_save', 'tone_change', 'language_change', 'regenerate', 'change_order_edit', 'restore', 'clear', 'analysis_apply', 'project_change'] as const
function reasonKey(reason: string) { return `workflow.reason.${reasons.find(value => value === reason) ?? 'manual_save'}` as const }

export function WorkflowControls() {
  const { workflow, draftError, currentDraftId, saveDraft, currentHistoryEntryId, result } = useStore()
  const t = useTranslations()
  const [revisions, setRevisions] = useState<WorkingRevision[]>([])
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)
  const [server, setServer] = useState<WorkingDraft | null>(null)
  if (!workflow || !currentDraftId) return null
  async function action(operation: () => Promise<unknown>) {
    setBusy(true); setFailed(false)
    try { await operation() } catch { setFailed(true) } finally { setBusy(false) }
  }
  return <section className="mb-4 rounded-lg border border-border bg-card p-4" aria-label={t('workflow.workingState')}>
    <p role="status" className="text-sm">{t(`workflow.${workflow.status}`)}</p>
    {workflow.stale && result && <p className="mt-2 text-sm">{t('workflow.stale')}</p>}
    {workflow.archived && <p className="mt-2 text-sm">{t('workflow.archived')}</p>}
    {workflow.recovery && <div className="mt-3 rounded-lg border p-3"><p>{t('workflow.recovery')}</p><div className="mt-2 flex gap-2"><Button onClick={workflow.acceptRecovery}>{t('workflow.recover')}</Button><Button variant="outline" onClick={workflow.discardRecovery}>{t('workflow.discard')}</Button></div></div>}
    {workflow.status === 'conflict' && <div className="mt-3 rounded-lg border p-3"><p>{t('workflow.conflictHelp')}</p><Button variant="outline" disabled={busy} onClick={() => void action(async () => setServer(await workflow.compareConflict()))}>{t('workflow.reviewServer')}</Button>{server && <div className="mt-3"><h3 className="font-medium">{t('workflow.serverVersion')}</h3><p className="whitespace-pre-wrap">{server.requestText}</p><p className="mt-2 whitespace-pre-wrap">{server.draftDocument.reply.text}</p>{server.draftDocument.changeOrder && <p className="mt-2 whitespace-pre-wrap">{server.draftDocument.changeOrder.description} · {server.draftDocument.changeOrder.additionalCost} {server.draftDocument.changeOrder.currency}</p>}<div className="mt-2 flex flex-wrap gap-2"><Button disabled={busy} onClick={() => void action(async () => { await workflow.resolveConflict(true); setServer(null) })}>{t('workflow.reapply')}</Button><Button disabled={busy} variant="outline" onClick={() => void action(async () => { await workflow.resolveConflict(false); setServer(null) })}>{t('workflow.useServer')}</Button></div></div>}</div>}
    <div className="mt-3 flex flex-wrap gap-2">
      <Button variant="outline" disabled={busy || workflow.archived || workflow.status === 'conflict'} onClick={() => void action(saveDraft)}>{t(workflow.status === 'failed' ? 'workflow.retrySave' : 'workflow.saveNow')}</Button>
      <Button disabled={busy || workflow.stale || workflow.archived || workflow.status === 'conflict'} onClick={() => void action(workflow.complete)}>{t('workflow.complete')}</Button>
      <Button variant="outline" disabled={busy} onClick={() => void action(async () => setRevisions(await workflow.revisions()))}>{t('workflow.revisions')}</Button>
    </div>
    {currentHistoryEntryId && <p role="status" className="mt-2 text-sm">{t('workflow.completed')}</p>}
    {(draftError || failed) && <p role="alert" className="mt-2 text-sm">{draftError ? t(draftError) : t('errors.requestFailed')}</p>}
    {revisions.length > 0 && <ul className="mt-3 max-h-64 space-y-2 overflow-auto">{revisions.map(revision => <li key={revision.id} className="flex items-center justify-between gap-3 rounded border p-2 text-sm"><span>{t('workflow.revision', { number: revision.revision })} · {revision.reason === 'legacy_import' ? t('workflow.legacyImport') : t(reasonKey(revision.reason))}</span><Button variant="outline" disabled={busy || workflow.archived} onClick={() => void action(async () => { await workflow.restore(revision.revision); setRevisions([]) })}>{t('workflow.restore')}</Button></li>)}</ul>}
  </section>
}
