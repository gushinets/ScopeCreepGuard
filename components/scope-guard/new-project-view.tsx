'use client'

import { useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { Industry } from '@/lib/types'
import { useStore } from './store'

const INDUSTRIES: Industry[] = ['Development', 'Design', 'Marketing']

export function NewProjectView() {
  const { createProject, setView } = useStore()

  const [name, setName] = useState('')
  const [client, setClient] = useState('')
  const [industry, setIndustry] = useState<Industry>('Design')
  const [scope, setScope] = useState('')
  const [touched, setTouched] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState('')

  const nameError = touched && name.trim().length === 0

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setTouched(true)
    setSaveError('')
    if (name.trim().length === 0) return

    setIsSaving(true)
    try {
      await createProject({ name, client, industry, scope })
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'new_project_submit_failed',
          message: error instanceof Error ? error.message : 'Unknown project error',
        }),
      )
      setSaveError(
        error instanceof Error ? error.message : 'Unable to save this project.',
      )
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <button
        type="button"
        onClick={() => setView('projects')}
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back to projects
      </button>

      <h2 className="mt-4 text-xl font-semibold text-foreground">New project</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Save the agreed scope once — then check every future request against it.
      </p>

      <form onSubmit={submit} className="mt-6 flex flex-col gap-5">
        <div>
          <label
            htmlFor="np-name"
            className="mb-1.5 block text-sm font-medium text-foreground"
          >
            Project name
          </label>
          <input
            id="np-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Acme website redesign"
            aria-invalid={nameError}
            className={cn(
              'w-full rounded-lg border bg-background px-3 py-2 text-sm text-foreground outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring/40',
              nameError
                ? 'border-outscope focus-visible:border-outscope'
                : 'border-input focus-visible:border-ring',
            )}
          />
          {nameError && (
            <p className="mt-1 text-xs text-outscope-text">
              A project name is required.
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="np-client"
            className="mb-1.5 block text-sm font-medium text-foreground"
          >
            Client name{' '}
            <span className="font-normal text-muted-foreground">(optional)</span>
          </label>
          <input
            id="np-client"
            value={client}
            onChange={(e) => setClient(e.target.value)}
            placeholder="e.g. Acme Inc."
            className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40"
          />
        </div>

        <div>
          <span className="mb-1.5 block text-sm font-medium text-foreground">
            Industry
          </span>
          <div
            role="radiogroup"
            aria-label="Industry"
            className="inline-flex rounded-lg border border-border bg-muted p-0.5"
          >
            {INDUSTRIES.map((i) => (
              <button
                key={i}
                type="button"
                role="radio"
                aria-checked={industry === i}
                onClick={() => setIndustry(i)}
                className={cn(
                  'rounded-md px-3 py-1.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  industry === i
                    ? 'bg-card text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {i}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label
            htmlFor="np-scope"
            className="mb-1.5 block text-sm font-medium text-foreground"
          >
            Agreed scope
          </label>
          <textarea
            id="np-scope"
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            rows={10}
            placeholder="Paste the deliverables, revision rounds, and exclusions here…"
            className="w-full resize-y rounded-lg border border-input bg-background p-3 text-sm leading-relaxed text-foreground outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40"
          />
          <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
            Tip: paste directly from your contract, proposal, or SOW. Include both
            what&apos;s delivered and what&apos;s excluded for the sharpest verdicts.
          </p>
        </div>

        {saveError && (
          <p className="rounded-lg bg-outscope-soft px-3 py-2 text-sm text-outscope-text">
            {saveError}
          </p>
        )}

        <div className="flex items-center gap-2">
          <Button type="submit" className="h-9" disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save project'}
          </Button>
          <Button
            type="button"
            variant="ghost"
            className="h-9"
            onClick={() => setView('projects')}
          >
            Cancel
          </Button>
        </div>
      </form>
    </div>
  )
}
