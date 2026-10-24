import { useState } from 'react'
import { useLocale, useTranslations } from 'use-intl'
import { Button } from '@/shared/ui/button'
import { useDrafts } from './context'

export function DraftExportAction() {
  const { currentDraftId, workflow, exportCurrentDraft } = useDrafts()
  const t = useTranslations('drafts'), locale = useLocale()
  const [pending, setPending] = useState(false), [failed, setFailed] = useState(false)
  if (!currentDraftId || workflow.archived || workflow.legacyRevision) return null
  async function download() {
    if (pending) return
    setPending(true); setFailed(false)
    try { await exportCurrentDraft(locale === 'ru' ? 'ru' : 'en') }
    catch { setFailed(true) }
    finally { setPending(false) }
  }
  return <div className="flex max-w-sm flex-col items-end gap-2">
    <Button type="button" variant="outline" disabled={pending || !!workflow.recovery} onClick={() => void download()}>{t(pending ? 'exporting' : 'exportDraft')}</Button>
    {failed && <p role="alert" className="text-sm text-outscope-text">{t('exportFailed')}</p>}
  </div>
}
