import { useEffect, useState } from 'react'
import { useLocale, useTranslations } from 'use-intl'
import { workflowApi, type WorkingDraft } from '@/features/drafts/contracts'
import type { PersistentProject } from '@/features/projects'
import { AgreementPdfDownload, ChangeOrderDocumentPreview, downloadChangeOrder } from '@/features/change-orders'
import { Button } from '@/shared/ui/button'

/** Archive browsing reads the retained draft without installing an active editor. */
export function ArchivedDraft({ project }: { project: PersistentProject }) {
  const t = useTranslations()
  const locale = useLocale()
  const [draft, setDraft] = useState<WorkingDraft | null>(null)
  const [failed, setFailed] = useState(false)
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const request = new AbortController()
    void workflowApi<{ draft: WorkingDraft }>(`projects/${project.id}/draft`, undefined, 'GET', request.signal)
      .then(value => { if (!request.signal.aborted) { setDraft(value.draft); setFailed(false) } })
      .catch(() => { if (!request.signal.aborted) setFailed(true) })
    return () => request.abort()
  }, [project.id, attempt])
  if (failed) return <div><p role="alert">{t('history.savedDraftFailed')}</p><Button variant="outline" onClick={() => { setFailed(false); setAttempt(value => value + 1) }}>{t('result.tryAgain')}</Button></div>
  if (!draft) return <p role="status">{t('history.loadingSavedDraft')}</p>
  const document = draft.draftDocument.changeOrder
  return <article className="history-detail" aria-label={t('history.savedDraft')}>
    <h2>{t('history.savedDraft')}</h2>
    <time className="mt-1 block text-xs text-muted-foreground" dateTime={draft.updatedAt}>{new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(draft.updatedAt))}</time>
    <h3 className="mt-4 text-sm font-semibold">{t('projects.scopeLabel')}</h3><p className="mt-1 whitespace-pre-wrap text-sm">{project.scope}</p>
    {draft.requestText && <><h3 className="mt-4 text-sm font-semibold">{t('result.clientRequest')}</h3><p className="mt-1 whitespace-pre-wrap text-sm">{draft.requestText}</p></>}
    {draft.draftDocument.reply.text && <><h3 className="mt-4 text-sm font-semibold">{t('reply.heading')}</h3><p className="mt-1 whitespace-pre-wrap text-sm">{draft.draftDocument.reply.text}</p></>}
    {document && <div className="mt-5"><ChangeOrderDocumentPreview draft={document} /><div className="mt-4 flex flex-wrap gap-2"><AgreementPdfDownload language={document.language} download={signal => downloadChangeOrder({ draft: document, projectId: project.id, persistentWorkflow: true }, signal)} /></div></div>}
  </article>
}
