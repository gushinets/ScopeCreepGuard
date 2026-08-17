'use client'

import { ArrowRight, FolderPlus, Plus } from 'lucide-react'
import { useLocale, useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { localeToDateLocale, type Locale } from '@/i18n/config'
import type { Industry } from '@/lib/types'
import { useStore } from './store'

function formatDate(iso: string, locale: Locale) {
  const d = new Date(iso)
  return d.toLocaleDateString(localeToDateLocale(locale), {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function industryLabelKey(industry: Industry) {
  return `industry.${industry}` as const
}

export function ProjectsView() {
  const { projects, selectProject, setView } = useStore()
  const locale = useLocale()
  const t = useTranslations()

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-foreground">
            {t('projects.title')}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {t('projects.description')}
          </p>
        </div>
        <Button type="button" className="h-9" onClick={() => setView('new_project')}>
          <Plus aria-hidden="true" />
          {t('projects.newProject')}
        </Button>
      </div>

      {projects.length === 0 ? (
        <div className="mt-8 rounded-xl border border-dashed border-border bg-card/50 p-10 text-center">
          <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-muted">
            <FolderPlus className="size-6 text-muted-foreground" aria-hidden="true" />
          </span>
          <h3 className="mt-4 text-base font-semibold text-foreground">
            {t('projects.emptyTitle')}
          </h3>
          <p className="mx-auto mt-1.5 max-w-sm text-sm text-muted-foreground text-pretty">
            {t('projects.emptyDescription')}
          </p>
          <Button
            type="button"
            className="mt-4 h-9"
            onClick={() => setView('new_project')}
          >
            <Plus aria-hidden="true" />
            {t('projects.createFirst')}
          </Button>
        </div>
      ) : (
        <ul className="mt-6 divide-y divide-border overflow-hidden rounded-xl border border-border bg-card">
          {projects.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                onClick={() => {
                  selectProject(p.id)
                  setView('check')
                }}
                className="flex w-full items-center justify-between gap-4 px-4 py-3.5 text-left transition-colors hover:bg-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-foreground">
                    {p.name}
                  </p>
                  <p className="mt-0.5 truncate text-xs text-muted-foreground">
                    {p.client ? `${p.client} · ` : ''}
                    {t(industryLabelKey(p.industry))} ·{' '}
                    {p.lastChecked
                      ? t('projects.lastChecked', {
                          date: formatDate(p.lastChecked, locale),
                        })
                      : t('projects.notCheckedYet')}
                  </p>
                </div>
                <ArrowRight
                  className="size-4 shrink-0 text-muted-foreground"
                  aria-hidden="true"
                />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
