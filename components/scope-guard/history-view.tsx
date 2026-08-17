'use client'

import { Clock } from 'lucide-react'
import { useLocale, useTranslations } from 'next-intl'
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
  const { selectedProject } = useStore()
  const locale = useLocale()
  const t = useTranslations()

  if (!selectedProject) {
    return (
      <div className="mx-auto max-w-2xl text-center text-sm text-muted-foreground">
        {t('history.selectProject')}
      </div>
    )
  }

  const { history } = selectedProject

  return (
    <div className="mx-auto max-w-2xl">
      <h2 className="text-xl font-semibold text-foreground">
        {t('history.title')}
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        {t('history.previousChecks', {
          projectName: selectedProject.name,
        })}
      </p>

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
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
