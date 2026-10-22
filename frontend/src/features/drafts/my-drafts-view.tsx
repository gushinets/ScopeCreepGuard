import { useEffect, useState } from 'react'
import { useLocale, useTranslations } from 'use-intl'
import { Button } from '@/shared/ui/button'
import { ERROR_CODES, type ErrorCode } from '@/shared/api/errors'
import { localeToDateLocale } from '@/shared/i18n/config'
import type { DraftListItem } from '@/features/drafts/model/types'
import { useDrafts } from './context'

export function MyDraftsView() {
  const { listDrafts, openDraft, draftError } = { ...useDrafts() }
  const t = useTranslations()
  const locale = useLocale()
  const [drafts, setDrafts] = useState<DraftListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ErrorCode | ''>('')
  const [refresh, setRefresh] = useState(0)
  const [openingId, setOpeningId] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void listDrafts().then((items) => { if (active) setDrafts(items) })
      .catch(() => { if (active) setError(ERROR_CODES.draftLoadFailed) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [listDrafts, refresh])

  async function open(id: string) {
    setOpeningId(id)
    try { await openDraft(id) } catch { /* The store exposes localized opening errors. */ }
    finally { setOpeningId(null) }
  }

  return <section>
    <div className="screen-heading"><div><h1>{t('drafts.title')}</h1><p>{t('drafts.description')}</p></div></div>
    {loading ? <p role="status" className="mt-6 text-sm text-muted-foreground">{t('drafts.loading')}</p> :
      error ? <div className="mt-6"><p role="alert" className="text-sm text-outscope-text">{t(error)}</p><Button type="button" variant="outline" className="mt-3" onClick={() => { setLoading(true); setError(''); setRefresh((value) => value + 1) }}>{t('drafts.retry')}</Button></div> :
      drafts.length === 0 ? <div className="collection-empty"><h3 className="font-semibold">{t('drafts.emptyTitle')}</h3><p className="mt-1 text-sm text-muted-foreground">{t('drafts.emptyDescription')}</p></div> :
      <ul className="draft-rows">
        {drafts.map((draft) => <li key={draft.id}>
          <button type="button" disabled={!!openingId} onClick={() => void open(draft.id)} className="block w-full min-w-0 px-4 py-3 text-left transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60">
            <span className="block truncate text-sm font-medium">{draft.requestPreview}</span>
            <span className="mt-1 block truncate text-xs text-muted-foreground">{draft.projectName} · {draft.verdict ? t(`verdict.${draft.verdict}`) : t('workflow.noAnalysis')} · <time dateTime={draft.createdAt}>{new Date(draft.createdAt).toLocaleDateString(localeToDateLocale(locale), { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' })}</time>{openingId === draft.id ? ` · ${t('drafts.opening')}` : ''}</span>
          </button>
        </li>)}
      </ul>}
    {draftError && <p role="alert" className="mt-3 text-sm text-outscope-text">{t(draftError)}</p>}
  </section>
}
