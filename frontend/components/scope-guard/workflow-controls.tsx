'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { useStore } from './store'

export function WorkflowControls() {
  const { workflow, draftError, currentDraftId, result } = useStore()
  const t = useTranslations()
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)
  if (!workflow || !currentDraftId || workflow.status === 'conflict' || workflow.recovery) return null
  async function action(operation: () => Promise<unknown>) {
    setBusy(true); setFailed(false)
    try { await operation() } catch { setFailed(true) } finally { setBusy(false) }
  }
  return <section className="mb-4 rounded-lg border border-border bg-card p-4" aria-label={t('workflow.workingState')}>
    <p role="status" className="text-sm">{t(`workflow.${workflow.status}`)}</p>
    {workflow.stale && result && <p className="mt-2 text-sm">{t('workflow.stale')}</p>}
    {workflow.archived && <p className="mt-2 text-sm">{t('workflow.archived')}</p>}
    <div className="mt-3 flex flex-wrap gap-2">
      {workflow.status === 'failed' && <Button variant="outline" disabled={busy || workflow.archived} onClick={() => void action(workflow.retrySave)}>{t('workflow.retrySave')}</Button>}
      <Button disabled={busy || workflow.stale || workflow.archived} onClick={() => void action(workflow.complete)}>{t('workflow.complete')}</Button>
    </div>
    {(draftError || failed) && <p role="alert" className="mt-2 text-sm">{draftError ? t(draftError) : t('errors.requestFailed')}</p>}
  </section>
}
