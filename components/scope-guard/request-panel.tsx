'use client'

import { useState } from 'react'
import { ChevronDown, FolderPlus, ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { EXAMPLE_REQUESTS } from '@/lib/mock-data'
import { useStore } from './store'

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
  } = useStore()

  const [scopeOpen, setScopeOpen] = useState(false)

  if (!selectedProject) {
    return (
      <div className="rounded-xl border border-border bg-card p-6 text-center">
        <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-muted">
          <FolderPlus className="size-6 text-muted-foreground" aria-hidden="true" />
        </span>
        <h3 className="mt-4 text-base font-semibold text-foreground">
          No project selected
        </h3>
        <p className="mt-1.5 text-sm text-muted-foreground text-pretty">
          Create a project and save its scope to start checking client requests.
        </p>
        <Button
          type="button"
          className="mt-4 h-9"
          onClick={() => setView('new_project')}
        >
          <FolderPlus aria-hidden="true" />
          New project
        </Button>
      </div>
    )
  }

  const hasScope = selectedProject.scope.trim().length > 0
  const requestEmpty = requestText.trim().length === 0
  const busy = status === 'loading'

  return (
    <div className="flex flex-col gap-4">
      {/* Project selector */}
      <div>
        <label
          htmlFor="project-select"
          className="mb-1.5 block text-xs font-medium text-muted-foreground"
        >
          Project
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
                {p.client ? ` · ${p.client}` : ''}
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
            Agreed scope
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-normal text-muted-foreground">
              {selectedProject.industry}
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
              This project has no saved scope yet.
            </p>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              Add the deliverables and exclusions from your contract or SOW so
              requests can be compared against them.
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
            New client request
          </label>
          <div className="flex flex-wrap items-center gap-1">
            <span className="mr-1 text-[11px] text-muted-foreground">Try:</span>
            {EXAMPLE_REQUESTS.map((ex) => (
              <button
                key={ex.key}
                type="button"
                onClick={() => loadExample(ex.text, ex.key === 'error')}
                className="rounded-full border border-border bg-card px-2 py-0.5 text-[11px] font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {ex.label}
              </button>
            ))}
          </div>
        </div>
        <textarea
          id="request-input"
          value={requestText}
          onChange={(e) => setRequestText(e.target.value)}
          rows={6}
          placeholder="Paste the message or request your client just sent…"
          className="w-full resize-y rounded-lg border border-input bg-background p-3 text-sm leading-relaxed text-foreground outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40"
        />
      </div>

      <div className="flex flex-col gap-2">
        <Button
          type="button"
          onClick={runCheck}
          disabled={requestEmpty || !hasScope || busy}
          className="h-11 w-full text-sm"
        >
          <ShieldCheck aria-hidden="true" />
          {busy ? 'Checking…' : 'Check scope'}
        </Button>
        {requestEmpty && (
          <p className="text-xs text-muted-foreground">
            Paste a client request above to run a check.
          </p>
        )}
      </div>
    </div>
  )
}
