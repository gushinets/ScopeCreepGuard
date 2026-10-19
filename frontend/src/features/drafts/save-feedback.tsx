import { useTranslations } from 'use-intl'
import { Button } from '@/shared/ui/button'
import { useDrafts } from './context'

export function SaveFeedback() {
  const { workflow, currentDraftId, draftError } = { ...useDrafts() }
  const t = useTranslations()
  if (!workflow || !currentDraftId) return null
  const failed = workflow.status === 'failed' || workflow.status === 'conflict'
  const unconfirmed = failed || !!workflow.recovery
  return <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-border p-3">
    <p role={unconfirmed ? 'alert' : 'status'} className={unconfirmed ? 'text-sm text-outscope-text' : 'text-xs text-muted-foreground'}>
      {t(unconfirmed ? 'workflow.failed' : workflow.status === 'saved' ? 'workflow.saved' : 'workflow.saving')}
    </p>
    {failed && <>
      {draftError && <p className="text-xs text-muted-foreground">{t(draftError)}</p>}
      <Button type="button" variant="outline" onClick={() => { void workflow.retrySave().catch(() => {}) }}>{t('workflow.retrySave')}</Button>
    </>}
    {workflow.recovery && <div className="flex flex-wrap items-center gap-3">
      <p className="text-sm">{t('workflow.recovery')}</p>
      <Button type="button" variant="outline" disabled={workflow.status !== 'saved'} onClick={() => { workflow.acceptRecovery(); void workflow.retrySave().catch(() => {}) }}>{t('workflow.recover')}</Button>
      <Button type="button" variant="ghost" onClick={workflow.discardRecovery}>{t('workflow.discard')}</Button>
    </div>}
  </div>
}
