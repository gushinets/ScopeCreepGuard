import { OnboardingSlot } from '@/features/onboarding'
import { useState } from 'react'
import { ChevronDown, FolderPlus, ShieldCheck, ArrowRight } from 'lucide-react'
import { useTranslations } from 'use-intl'
import { Button } from '@/shared/ui/button'
import { cn } from '@/shared/ui/utils'
import { EXAMPLE_REQUESTS } from '@/features/analysis/model/mock-data'
import type { Industry } from '@/shared/api/models'
import { useProjects } from '@/features/projects'
import { useDrafts } from '@/features/drafts'
import { useAnalysis } from './operations'
import { useWorkspaceNavigation } from '@/shared/ui/navigation'

function industryLabelKey(industry: Industry) {
  return `industry.${industry}` as const
}

function exampleLabelKey(key: (typeof EXAMPLE_REQUESTS)[number]['key']) {
  return `examples.${key}` as const
}

function exampleTextKey(key: (typeof EXAMPLE_REQUESTS)[number]['key']) {
  return `examples.${key}Text` as const
}

export function RequestPanel() {
  const {
    projects,
    selectedProject,
    selectedProjectId,
    selectProject,
    requestText,
    setRequestText,
    runCheck,
    status,
    setView,
    loadExample,
    workflow,
  } = { ...useProjects(), ...useDrafts(), ...useAnalysis(), ...useWorkspaceNavigation() }
  const t = useTranslations()

  const [scopeOpen, setScopeOpen] = useState(false)

  if (!selectedProject) {
    return <div className="first-project project-start">
      <section className="first-project-copy">
        <h2>{t('projects.emptyTitle')}</h2>
        <p>{t('check.noProjectDescription')}</p>
        <Button type="button" data-onboarding="create-project" onClick={() => setView('new_project')}><FolderPlus size={16} aria-hidden="true" />{t('projects.createFirst')}<ArrowRight size={16} aria-hidden="true" /></Button>
        <OnboardingSlot step={0} />
      </section>
    </div>
  }

  const hasScope = selectedProject.scope.trim().length > 0
  const requestEmpty = requestText.trim().length === 0
  const busy = status === 'loading'

  return (
    <section className="request-workspace flex flex-col gap-4"><h2 className="request-title">{t('design.sourceMaterial')}</h2>
      {/* Project selector */}
      <div>
        <label
          htmlFor="project-select"
          className="mb-1.5 block text-xs font-medium text-muted-foreground"
        >
          {t('check.projectLabel')}
        </label>
        <div className="relative">
          <select
            id="project-select"
            value={selectedProjectId ?? ''}
            onChange={(e) => selectProject(e.target.value)}
            className="w-full appearance-none rounded-lg border border-input bg-background py-2 pr-9 pl-3 text-sm font-medium text-foreground outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <ChevronDown
            className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
        </div>
      </div>

      {/* Scope summary */}
      <div className="rounded-lg border border-border bg-card">
        <button
          type="button"
          onClick={() => setScopeOpen((v) => !v)}
          aria-expanded={scopeOpen}
          className="flex w-full items-center justify-between gap-2 px-3.5 py-2.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="flex items-center gap-2 text-sm font-medium text-foreground">
            <ShieldCheck className="size-4 text-muted-foreground" aria-hidden="true" />
            {t('check.agreedScope')}
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-normal text-muted-foreground">
              {t(industryLabelKey(selectedProject.industry))}
            </span>
          </span>
          <ChevronDown
            className={cn(
              'size-4 shrink-0 text-muted-foreground transition-transform',
              scopeOpen && 'rotate-180',
            )}
            aria-hidden="true"
          />
        </button>

        {!hasScope ? (
          <div className="border-t border-border px-3.5 py-3">
            <p className="text-sm text-borderline-text">
              {t('check.noScopeTitle')}
            </p>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              {t('check.noScopeDescription')}
            </p>
          </div>
        ) : (
          <div
            className={cn(
              'overflow-hidden border-border text-sm text-foreground/80',
              scopeOpen ? 'border-t' : '',
            )}
          >
            <pre
              className={cn(
                'max-h-64 overflow-auto whitespace-pre-wrap px-3.5 py-3 font-sans leading-relaxed',
                scopeOpen ? 'block' : 'line-clamp-3 max-h-16',
              )}
            >
              {scopeOpen
                ? selectedProject.scope
                : selectedProject.scope.split('\n').slice(0, 3).join(' ')}
            </pre>
          </div>
        )}
      </div>

      {/* New client request */}
      <div>
        <div className="mb-1.5 flex items-center justify-between gap-2">
          <label
            htmlFor="request-input"
            className="text-xs font-medium text-muted-foreground"
          >
            {t('check.requestLabel')}
          </label>
          <div className="flex flex-wrap items-center gap-1">
            <span className="mr-1 text-[11px] text-muted-foreground">
              {t('check.tryLabel')}
            </span>
            {EXAMPLE_REQUESTS.map((ex) => (
              <button
                key={ex.key}
                type="button"
                onClick={() => loadExample(t(exampleTextKey(ex.key)))}
                className="rounded border border-border bg-card px-2 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {t(exampleLabelKey(ex.key))}
              </button>
            ))}
          </div>
        </div>
        <OnboardingSlot step={2} />
        <textarea
          id="request-input"
          readOnly={!!workflow?.archived}
          value={requestText}
          onChange={(e) => setRequestText(e.target.value)}
          rows={6}
          placeholder={t('check.requestPlaceholder')}
          className="w-full resize-y rounded-lg border border-input bg-background p-3 text-sm leading-relaxed text-foreground outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40"
        />
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-xs leading-relaxed text-muted-foreground">
          {t('check.openaiNotice')}
        </p>
        <Button
          type="button"
          onClick={runCheck}
          disabled={requestEmpty || !hasScope || busy || !!workflow?.archived}
          className="h-11 w-full text-sm"
        >
          <ShieldCheck aria-hidden="true" />
          {busy ? t('check.checking') : t('check.checkScope')}
        </Button>
        {requestEmpty && (
          <p className="text-xs text-muted-foreground">
            {t('check.requestRequiredHint')}
          </p>
        )}
      </div>
    </section>
  )
}
