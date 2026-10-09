'use client'

import { useState } from 'react'
import { Clock } from 'lucide-react'
import { useLocale, useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { assertErrorCode, type ErrorCode } from '@/lib/api/errors'
import { localeToDateLocale, type Locale } from '@/i18n/config'
import { VerdictChip } from './verdict'
import { useStore } from './store'

function formatDate(iso: string, locale: Locale) {
  return new Date(iso).toLocaleDateString(localeToDateLocale(locale), {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function HistoryView() {
  const { selectedProject, downloadEvaluationsExport, openDraft, draftError } = useStore()
  const locale = useLocale()
  const t = useTranslations()
  const [isDownloading, setIsDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<ErrorCode | ''>('')
  const [openingId, setOpeningId] = useState<string | null>(null)

  if (!selectedProject) {
    return (
      <div className="mx-auto max-w-2xl text-center text-sm text-muted-foreground">
        {t('history.selectProject')}
      </div>
    )
  }

  const { history } = selectedProject

  async function onDownload() {
    setIsDownloading(true)
    setDownloadError('')
    try {
      await downloadEvaluationsExport()
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'evaluation_download_failed',
          message: error instanceof Error ? error.message : 'Unknown download error',
        }),
      )
      if (!(error instanceof Error)) {
        throw new Error('Unknown download error')
      }
      setDownloadError(assertErrorCode(error.message))
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-foreground">
            {t('history.title')}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {t('history.previousChecks', {
              projectName: selectedProject.name,
            })}
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          className="h-9"
          disabled={isDownloading}
          onClick={() => {
            void onDownload()
          }}
        >
          {isDownloading
            ? t('history.downloadingEvaluations')
            : t('history.downloadEvaluations')}
        </Button>
      </div>
      {draftError && <p role="alert" className="mt-3 text-sm text-outscope-text">{t(draftError)}</p>}
      {downloadError ? (
        <p className="mt-3 text-sm text-outscope-text" role="alert">
          {t(downloadError)}
        </p>
      ) : null}

      {history.length === 0 ? (
        <div className="mt-6 rounded-xl border border-dashed border-border bg-card/50 p-10 text-center">
          <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-muted">
            <Clock className="size-6 text-muted-foreground" aria-hidden="true" />
          </span>
          <h3 className="mt-4 text-base font-semibold text-foreground">
            {t('history.emptyTitle')}
          </h3>
          <p className="mx-auto mt-1.5 max-w-sm text-sm text-muted-foreground text-pretty">
            {t('history.emptyDescription')}
          </p>
        </div>
      ) : (
        <ul className="mt-6 flex flex-col gap-3">
          {history.map((h) => (
            <li
              key={h.id}
              className="rounded-lg border border-border bg-card p-4"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs text-muted-foreground">
                  {formatDate(h.date, locale)}
                </span>
                <VerdictChip verdict={h.verdict} />
              </div>
              <p className="mt-2 text-sm leading-relaxed text-foreground text-pretty">
                {h.request}
              </p>
              <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground text-pretty">
                {h.summary}
              </p>
              {h.draftId && <Button type="button" variant="outline" className="mt-3" disabled={!!openingId} onClick={() => { setOpeningId(h.id); void openDraft(h.draftId!).catch(() => {}).finally(() => setOpeningId(null)) }}>{t(openingId === h.id ? 'drafts.opening' : 'history.openDraft')}</Button>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
