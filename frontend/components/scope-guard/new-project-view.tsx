'use client'

import { useRef, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { assertErrorCode, type ErrorCode } from '@/lib/api/errors'
import { readScopeFile } from '@/lib/scope/read-file'
import { projectFieldErrors, validISODate } from '@/lib/projects/validation'
import { readProjectDetails, writeProjectDetails, type ProjectDetails } from '@/lib/projects/browser-details'
import type { Currency, Industry, PricingModel } from '@/lib/types'
import { DeleteProjectAction } from './delete-project-action'
import { useStore } from './store'

type Fields = { name: string; scope: string; industry: Industry; startDate: string; pricingModel: PricingModel; currency: Currency; hourlyRate: string; fixedPrice: string }
const emptyDetails: ProjectDetails = { clientName: '', clientEmail: '', endDate: '' }
const industries: Industry[] = ['Development', 'Design', 'Marketing']

export function NewProjectView({ edit = false }: { edit?: boolean }) {
  const { createProject, updateProject, selectedProject, user, setView } = useStore()
  const project = edit ? selectedProject : null
  const t = useTranslations()
  const [fields, setFields] = useState<Fields>({
    name: project?.name ?? '', scope: project?.scope ?? '', industry: project?.industry ?? 'Design',
    startDate: project?.startDate ?? '', pricingModel: project?.pricingModel ?? 'hourly',
    currency: project?.currency ?? 'RUB', hourlyRate: project?.hourlyRate ?? '', fixedPrice: project?.fixedPrice ?? '',
  })
  const [details, setDetails] = useState<ProjectDetails>(() => project && user ? { ...readProjectDetails(user.id, project.id), clientName: project.clientName ?? readProjectDetails(user.id, project.id).clientName } : emptyDetails)
  const [attempted, setAttempted] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<ErrorCode | ''>('')
  const [uploadError, setUploadError] = useState<ErrorCode | ''>('')
  const fileInput = useRef<HTMLInputElement>(null)
  const form = useRef<HTMLFormElement>(null)

  function change<K extends keyof Fields>(key: K, value: Fields[K]) {
    setFields((current) => ({ ...current, [key]: value }))
  }
  function optional<K extends keyof ProjectDetails>(key: K, value: string) {
    setDetails((current) => ({ ...current, [key]: value }))
  }

  const errors = attempted ? projectFieldErrors(fields) : {}
  const emailInvalid = details.clientEmail.trim() !== '' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(details.clientEmail.trim())
  const endInvalid = details.endDate !== '' && (!validISODate(details.endDate) || (validISODate(fields.startDate) && details.endDate < fields.startDate))

  async function upload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setUploadError('')
    try { change('scope', await readScopeFile(file)) }
    catch (error) { setUploadError(assertErrorCode(error instanceof Error ? error.message : '')) }
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setAttempted(true)
    setSaveError('')
    const first = Object.keys(projectFieldErrors(fields))[0] ?? (emailInvalid ? 'clientEmail' : endInvalid ? 'endDate' : '')
    if (first) {
      requestAnimationFrame(() => form.current?.querySelector<HTMLElement>(`[name="${first}"]`)?.focus())
      return
    }
    setSaving(true)
    try {
      const saved = project ? await updateProject(project.id, { ...fields, clientName: details.clientName }, details) : await createProject({ ...fields, clientName: details.clientName })
      if (user && !project) writeProjectDetails(user.id, saved.id, details)
    } catch (error) {
      setSaveError(assertErrorCode(error instanceof Error ? error.message : ''))
    } finally { setSaving(false) }
  }

  function field(key: keyof Fields | keyof ProjectDetails, label: string, value: string, onChange: (value: string) => void, options: { optional?: boolean; type?: string; error?: string; placeholder?: string } = {}) {
    return <div key={key}>
      <label htmlFor={`project-${key}`} className="mb-1.5 block text-sm font-medium text-foreground">
        {label} <span className="font-normal text-muted-foreground">{options.optional ? t('projects.optional') : t('projects.required')}</span>
      </label>
      <input id={`project-${key}`} name={key} type={options.type ?? 'text'} value={value} onChange={(e) => onChange(e.target.value)} placeholder={options.placeholder}
        aria-invalid={!!options.error} aria-describedby={options.error ? `project-${key}-error` : undefined}
        className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40" />
      {options.error && <p id={`project-${key}-error`} className="mt-1 text-xs text-outscope-text" role="alert">{options.error}</p>}
    </div>
  }

  return <div className="mx-auto max-w-2xl">
    <button type="button" onClick={() => setView('projects')} className="inline-flex items-center gap-1.5 text-sm text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><ArrowLeft className="size-4" aria-hidden="true" />{t('projects.backToProjects')}</button>
    <h2 className="mt-4 text-xl font-semibold text-foreground">{t(project ? 'projects.editTitle' : 'projects.newTitle')}</h2>
    <p className="mt-1 text-sm text-muted-foreground">{t('projects.newDescription')}</p>
    <form ref={form} noValidate onSubmit={submit} className="mt-6 flex flex-col gap-5">
      {field('name', t('projects.nameLabel'), fields.name, (v) => change('name', v), { error: errors.name && t(errors.name), placeholder: t('projects.namePlaceholder') })}
      <div>
        <label htmlFor="project-industry" className="mb-1.5 block text-sm font-medium">{t('projects.industryLabel')} <span className="font-normal text-muted-foreground">{t('projects.required')}</span></label>
        <select id="project-industry" name="industry" value={fields.industry} onChange={(e) => change('industry', e.target.value as Industry)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-ring">{industries.map((i) => <option key={i} value={i}>{t(`industry.${i}`)}</option>)}</select>
      </div>
      <div>
        <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2"><label htmlFor="project-scope" className="text-sm font-medium">{t('projects.scopeLabel')} <span className="font-normal text-muted-foreground">{t('projects.required')}</span></label><Button type="button" variant="outline" className="h-8 text-xs" onClick={() => fileInput.current?.click()}>{t('projects.uploadScope')}</Button><input ref={fileInput} type="file" accept=".txt,.md,.pdf,text/plain,application/pdf" className="hidden" onChange={upload} /></div>
        <textarea id="project-scope" name="scope" value={fields.scope} onChange={(e) => change('scope', e.target.value)} rows={8} placeholder={t('projects.scopePlaceholder')} aria-invalid={!!errors.scope} aria-describedby={errors.scope ? 'project-scope-error' : undefined} className="w-full resize-y rounded-lg border border-input bg-background p-3 text-sm leading-relaxed focus-visible:ring-2 focus-visible:ring-ring" />
        {errors.scope && <p id="project-scope-error" className="text-xs text-outscope-text" role="alert">{t(errors.scope)}</p>}
        <p className="mt-1 text-xs text-muted-foreground">{t('projects.uploadHint')}</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {field('startDate', t('projects.startDate'), fields.startDate, (v) => change('startDate', v), { type: 'date', error: errors.startDate && t(errors.startDate) })}
        {field('endDate', t('projects.endDate'), details.endDate, (v) => optional('endDate', v), { type: 'date', optional: true, error: attempted && endInvalid ? t('projects.endDateError') : '' })}
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div><label htmlFor="project-pricingModel" className="mb-1.5 block text-sm font-medium">{t('projects.pricingModel')} <span className="font-normal text-muted-foreground">{t('projects.required')}</span></label><select id="project-pricingModel" name="pricingModel" value={fields.pricingModel} onChange={(e) => change('pricingModel', e.target.value as PricingModel)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-ring"><option value="hourly">{t('projects.hourly')}</option><option value="fixed">{t('projects.fixed')}</option></select></div>
        <div><label htmlFor="project-currency" className="mb-1.5 block text-sm font-medium">{t('projects.currency')} <span className="font-normal text-muted-foreground">{t('projects.required')}</span></label><select id="project-currency" name="currency" value={fields.currency} onChange={(e) => change('currency', e.target.value as Currency)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-ring">{(['RUB', 'USD', 'EUR'] as const).map((c) => <option key={c}>{c}</option>)}</select></div>
      </div>
      {fields.pricingModel === 'hourly' ? field('hourlyRate', t('projects.hourlyRate'), fields.hourlyRate, (v) => change('hourlyRate', v), { type: 'number', error: errors.hourlyRate && t(errors.hourlyRate) }) : field('fixedPrice', t('projects.fixedPrice'), fields.fixedPrice, (v) => change('fixedPrice', v), { type: 'number', error: errors.fixedPrice && t(errors.fixedPrice) })}
      <div className="grid gap-4 sm:grid-cols-2">
        {field('clientName', t('projects.clientLabel'), details.clientName, (v) => optional('clientName', v), { optional: true, placeholder: t('projects.clientPlaceholder') })}
        {field('clientEmail', t('projects.clientEmail'), details.clientEmail, (v) => optional('clientEmail', v), { optional: true, type: 'email', error: attempted && emailInvalid ? t('errors.invalidEmail') : '' })}
      </div>
      {uploadError && <p role="alert" className="text-sm text-outscope-text">{t(uploadError)}</p>}
      {saveError && <p role="alert" className="text-sm text-outscope-text">{t(saveError)}</p>}
      <div className="flex gap-2"><Button type="submit" disabled={saving}>{saving ? t('projects.saving') : t('projects.save')}</Button><Button type="button" variant="ghost" onClick={() => setView('projects')}>{t('projects.cancel')}</Button></div>
    </form>
    {project && <div className="mt-8 border-t border-border pt-5"><DeleteProjectAction project={project} disabled={saving} /></div>}
  </div>
}
