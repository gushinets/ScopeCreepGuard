import { useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router'
import { useLocale, useTranslations } from 'use-intl'
import { Button } from '@/shared/ui/button'
import { ERROR_CODES, type ErrorCode } from '@/shared/api/errors'
import { localeToDateLocale } from '@/shared/i18n/config'
import { useDrafts } from './context'
import { DEFAULT_DRAFT_FILTERS, readDraftFilters, writeDraftFilters, type DraftCollection, type DraftFilters } from './model/collection-client'
import { DraftFilterPopover } from './draft-filters'
import { DraftExportDialog } from './draft-export-dialog'

export function MyDraftsView() {
  const { listDrafts, openDraft, draftError, draftProjects } = useDrafts()
  const t = useTranslations(), locale = useLocale()
  const [query] = useSearchParams()
  const location = useLocation(), navigate = useNavigate()
  const queryText = query.toString()
  const { filters, invalid, offset } = useMemo(() => readDraftFilters(new URLSearchParams(queryText)), [queryText])
  const [collection, setCollection] = useState<DraftCollection>({ drafts: [], total: 0, hasDrafts: false })
  const [loading, setLoading] = useState(true), [error, setError] = useState<ErrorCode | ''>('')
  const [refresh, setRefresh] = useState(0), [openingId, setOpeningId] = useState<string | null>(null)
  const updateQuery = useCallback((next: DraftFilters, nextOffset = 0, replace = false) => {
    const params = writeDraftFilters(new URLSearchParams(location.search), next, nextOffset)
    void navigate({ pathname: location.pathname, search: params.size ? `?${params}` : '', hash: location.hash }, { state: location.state, replace })
  }, [location.pathname, location.search, location.hash, location.state, navigate])
  useEffect(() => {
    if (invalid) return
    let active = true
    setLoading(true); setError('')
    void listDrafts(filters, { limit: 50, offset }).then(items => {
      if (!active) return
      if (offset && offset >= items.total) { updateQuery(filters, 0, true); return }
      setCollection(items)
    }).catch(() => { if (active) setError(ERROR_CODES.draftLoadFailed) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [listDrafts, filters, invalid, offset, refresh, updateQuery])
  function apply(next: DraftFilters) { updateQuery(next) }
  const reset = () => apply(DEFAULT_DRAFT_FILTERS)
  async function open(id: string) {
    setOpeningId(id)
    try { await openDraft(id) } catch { /* Existing editor feedback exposes opening failures. */ }
    finally { setOpeningId(null) }
  }
  const date = (value: string) => new Date(value).toLocaleString(localeToDateLocale(locale), { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23', timeZone: 'UTC' })
  return <section>
    <div className="screen-heading flex-wrap gap-3"><div><h1>{t('drafts.title')}</h1><p>{t('drafts.description')}</p></div><div className="ml-auto flex flex-wrap gap-2"><DraftFilterPopover filters={filters} projects={draftProjects} onApply={apply} /><DraftExportDialog filters={filters} disabled={invalid} /></div></div>
    {invalid ? <div className="mt-6"><p role="alert">{t('drafts.invalidFilters')}</p><Button variant="outline" className="mt-3" onClick={reset}>{t('drafts.clearFilters')}</Button></div> :
      loading ? <p role="status" className="mt-6 text-sm text-muted-foreground">{t('drafts.loading')}</p> :
      error ? <div className="mt-6"><p role="alert" className="text-sm text-outscope-text">{t(error)}</p><Button type="button" variant="outline" className="mt-3" onClick={() => setRefresh(value => value + 1)}>{t('drafts.retry')}</Button></div> :
      collection.drafts.length === 0 ? <div className="collection-empty"><h3 className="font-semibold">{t(collection.hasDrafts ? 'drafts.noMatches' : 'drafts.emptyTitle')}</h3><p className="mt-1 text-sm text-muted-foreground">{t(collection.hasDrafts ? 'drafts.noMatchesDescription' : 'drafts.emptyDescription')}</p>{collection.hasDrafts && <Button className="mt-3" variant="outline" onClick={reset}>{t('drafts.clearFilters')}</Button>}</div> : <>
        <ul className="draft-rows">{collection.drafts.map(draft => <li key={draft.id}>
          <button type="button" disabled={!!openingId} onClick={() => void open(draft.id)} className="block w-full min-w-0 px-4 py-3 text-left transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60">
            <span className="block truncate text-sm font-medium">{draft.requestPreview || t('drafts.untitled')}</span>
            <span className="mt-1 block truncate text-xs text-muted-foreground">{draft.projectName} · {draft.verdict ? t(`verdict.${draft.verdict}`) : t('workflow.noAnalysis')}{openingId === draft.id ? ` · ${t('drafts.opening')}` : ''}</span>
            <span className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted-foreground"><span>{t('drafts.createdAt')} <time dateTime={draft.createdAt}>{date(draft.createdAt)}</time></span><span>{t('drafts.updatedAt')} <time dateTime={draft.updatedAt}>{date(draft.updatedAt)}</time></span></span>
          </button>
        </li>)}</ul>
        {collection.total > 50 && <nav aria-label={t('drafts.pagination')} className="mt-4 flex flex-wrap items-center justify-end gap-3"><span className="text-sm text-muted-foreground">{t('drafts.page', { page: offset / 50 + 1, pages: Math.ceil(collection.total / 50) })}</span><Button variant="outline" disabled={!offset} onClick={() => updateQuery(filters, offset - 50)}>{t('drafts.previous')}</Button><Button variant="outline" disabled={offset + 50 >= collection.total} onClick={() => updateQuery(filters, offset + 50)}>{t('drafts.next')}</Button></nav>}
      </>}
    {draftError && <p role="alert" className="mt-3 text-sm text-outscope-text">{t(draftError)}</p>}
  </section>
}
