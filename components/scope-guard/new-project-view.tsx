'use client'

import { useRef, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { assertErrorCode, type ErrorCode } from '@/lib/api/errors'
import { readScopeFile } from '@/lib/scope/read-file'
import type { Industry } from '@/lib/types'
import { useStore } from './store'

const INDUSTRIES: Industry[] = ['Development', 'Design', 'Marketing']

function industryLabelKey(industry: Industry) {
  return `industry.${industry}` as const
}

export function NewProjectView() {
  const { createProject, setView } = useStore()
  const t = useTranslations()

  const [name, setName] = useState('')
  const [client, setClient] = useState('')
  const [industry, setIndustry] = useState<Industry>('Design')
  const [scope, setScope] = useState('')
  const [touched, setTouched] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<ErrorCode | ''>('')
  const [uploadError, setUploadError] = useState<ErrorCode | ''>('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const nameError = touched && name.trim().length === 0

  async function onScopeFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return

    setUploadError('')
    try {
      const text = await readScopeFile(file)
      setScope(text)
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'scope_file_upload_failed',
          message: error instanceof Error ? error.message : 'Unknown upload error',
        }),
      )
      if (!(error instanceof Error)) {
        throw new Error('Unknown upload error')
      }
      setUploadError(assertErrorCode(error.message))
    }
  }

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
      if (!(error instanceof Error)) {
        throw new Error('Unknown project error')
      }
      setSaveError(assertErrorCode(error.message))
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
        {t('projects.backToProjects')}
      </button>

      <h2 className="mt-4 text-xl font-semibold text-foreground">
        {t('projects.newTitle')}
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        {t('projects.newDescription')}
      </p>

      <form onSubmit={submit} className="mt-6 flex flex-col gap-5">
        <div>
          <label
            htmlFor="np-name"
            className="mb-1.5 block text-sm font-medium text-foreground"
          >
            {t('projects.nameLabel')}
          </label>
          <input
            id="np-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t('projects.namePlaceholder')}
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
              {t('projects.nameRequired')}
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="np-client"
            className="mb-1.5 block text-sm font-medium text-foreground"
          >
            {t('projects.clientLabel')}{' '}
            <span className="font-normal text-muted-foreground">
              {t('projects.optional')}
            </span>
          </label>
          <input
            id="np-client"
            value={client}
            onChange={(e) => setClient(e.target.value)}
            placeholder={t('projects.clientPlaceholder')}
            className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40"
          />
        </div>

        <div>
          <span className="mb-1.5 block text-sm font-medium text-foreground">
            {t('projects.industryLabel')}
          </span>
          <div
            role="radiogroup"
            aria-label={t('projects.industryLabel')}
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
                {t(industryLabelKey(i))}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
            <label
              htmlFor="np-scope"
              className="text-sm font-medium text-foreground"
            >
              {t('projects.scopeLabel')}
            </label>
            <Button
              type="button"
              variant="outline"
              className="h-8 text-xs"
              onClick={() => fileInputRef.current?.click()}
            >
              {t('projects.uploadScope')}
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.md,.pdf,text/plain,application/pdf"
              className="hidden"
              onChange={onScopeFileChange}
            />
          </div>
          <textarea
            id="np-scope"
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            rows={10}
            placeholder={t('projects.scopePlaceholder')}
            className="w-full resize-y rounded-lg border border-input bg-background p-3 text-sm leading-relaxed text-foreground outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40"
          />
          <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
            {t('projects.uploadHint')}
          </p>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            {t('projects.scopeTip')}
          </p>
        </div>

        {uploadError && (
          <p className="rounded-lg bg-outscope-soft px-3 py-2 text-sm text-outscope-text">
            {t(uploadError)}
          </p>
        )}

        {saveError && (
          <p className="rounded-lg bg-outscope-soft px-3 py-2 text-sm text-outscope-text">
            {t(saveError)}
          </p>
        )}

        <div className="flex items-center gap-2">
          <Button type="submit" className="h-9" disabled={isSaving}>
            {isSaving ? t('projects.saving') : t('projects.save')}
          </Button>
          <Button
            type="button"
            variant="ghost"
            className="h-9"
            onClick={() => setView('projects')}
          >
            {t('projects.cancel')}
          </Button>
        </div>
      </form>
    </div>
  )
}
