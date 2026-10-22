import { useEffect, useRef, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { useTranslations } from 'use-intl'
import { Button } from '@/shared/ui/button'
import { assertErrorCode, type ErrorCode } from '@/shared/api/errors'
import { extractScope, type ExtractedScope } from './extraction'
import { ApiClientError } from '@/shared/api/client'
import { ERROR_CODES } from '@/shared/api/errors'
import { projectFieldErrors, validISODate } from '@/features/projects/model/validation'
import type { ProjectDetails } from './model/browser-details'
import type { Currency, Industry, PricingModel } from '@/shared/api/models'
import { DeleteProjectAction } from '@/features/projects/delete-project-action'
import { useProjects } from './resources'
import { useWorkspaceNavigation } from '@/shared/ui/navigation'
import { OnboardingSlot, useOnboarding } from '@/features/onboarding'

type Fields = { name: string; scope: string; industry: Industry; startDate: string; pricingModel: PricingModel; currency: Currency; hourlyRate: string; fixedPrice: string }
const emptyDetails: ProjectDetails = { clientName: '', clientEmail: '', endDate: '' }
const industries: Industry[] = ['Development', 'Design', 'Marketing']

export function NewProjectView({ edit = false }: { edit?: boolean }) {
  const { createProject, updateProject, selectedProject, setView, registerForm } = { ...useProjects(), ...useWorkspaceNavigation() }
  const project = edit ? selectedProject : null
  const t = useTranslations()
  const onboarding = useOnboarding()
  useEffect(() => { if (!edit) void onboarding.send('form_opened') }, [edit, onboarding.send])
  const [fields, setFields] = useState<Fields>({
    name: project?.name ?? '', scope: project?.scope ?? '', industry: project?.industry ?? 'Design',
    startDate: project?.startDate ?? '', pricingModel: project?.pricingModel ?? 'hourly',
    currency: project?.currency ?? 'RUB', hourlyRate: project?.hourlyRate ?? '', fixedPrice: project?.fixedPrice ?? '',
  })
  const [details, setDetails] = useState<ProjectDetails>(() => project ? { clientName: project.clientName ?? '', clientEmail: project.clientEmail ?? '', endDate: project.endDate ?? '' } : emptyDetails)
  const [attempted, setAttempted] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<ErrorCode | ''>('')
  const [uploadError, setUploadError] = useState<ErrorCode | ''>('')
  const [extracting, setExtracting] = useState(false)
  const [uploadWarnings, setUploadWarnings] = useState<ExtractedScope['warnings']>([])
  const extraction = useRef<AbortController | null>(null)
  useEffect(() => () => extraction.current?.abort(), [])
  const fileInput = useRef<HTMLInputElement>(null)
  const form = useRef<HTMLFormElement>(null)

  function change<K extends keyof Fields>(key: K, value: Fields[K]) {
    setFields((current) => ({ ...current, [key]: value }))
  }
  function changeScope(value: string) {
    extraction.current?.abort()
    extraction.current = null
    setExtracting(false)
    setUploadWarnings([])
    change('scope', value)
  }
  function optional<K extends keyof ProjectDetails>(key: K, value: string) {
    setDetails((current) => ({ ...current, [key]: value }))
  }

  const initialForm = useRef(JSON.stringify({ fields, details }))
  const latestForm = useRef({ dirty: false, saving: false })
  latestForm.current = { dirty: JSON.stringify({ fields, details }) !== initialForm.current, saving }
  useEffect(() => {
    const guard = () => !latestForm.current.dirty || latestForm.current.saving || window.confirm(t('projects.confirmLeave'))
    registerForm(guard)
    const unload = (event: BeforeUnloadEvent) => { if (latestForm.current.dirty && !latestForm.current.saving) { event.preventDefault(); event.returnValue = '' } }
    window.addEventListener('beforeunload', unload)
    return () => { registerForm(null); window.removeEventListener('beforeunload', unload) }
  }, [registerForm, t])

  const errors = attempted ? projectFieldErrors(fields) : {}
  const emailInvalid = details.clientEmail.trim() !== '' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(details.clientEmail.trim())
  const endInvalid = details.endDate !== '' && (!validISODate(details.endDate) || (validISODate(fields.startDate) && details.endDate < fields.startDate))

  async function upload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    extraction.current?.abort()
    const controller = new AbortController()
    extraction.current = controller
    setExtracting(true)
    setUploadError('')
    setUploadWarnings([])
    try {
      const result = await extractScope(file, controller.signal)
      if (extraction.current !== controller || controller.signal.aborted) return
      setFields((current) => ({ ...current, scope: result.text }))
      setUploadWarnings(result.warnings)
    } catch (error) {
      if (!controller.signal.aborted) setUploadError(error instanceof ApiClientError ? error.code : ERROR_CODES.scopeExtractFailed)
    } finally {
      if (extraction.current === controller) {
        extraction.current = null
        setExtracting(false)
      }
    }
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
      await (project ? await updateProject(project.id, { ...fields, clientName: details.clientName }, details) : await createProject({ ...fields, clientName: details.clientName, clientEmail: details.clientEmail || null, endDate: details.endDate || null }))
      if (!project) void onboarding.send('project_saved')
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

  return <div className="project-editor">
    <button type="button" onClick={() => setView('projects')} className="inline-flex items-center gap-1.5 text-sm text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"><ArrowLeft className="size-4" aria-hidden="true" />{t('projects.backToProjects')}</button>
    <div className="screen-heading mt-5"><div><h1>{t(project ? 'projects.editTitle' : 'projects.newTitle')}</h1><p>{t('projects.newDescription')}</p></div></div>
    <div className="project-editor-grid"><form ref={form} noValidate onSubmit={submit} className="project-editor-form">
      <section className="form-section"><h2>{t('design.projectDetails')}</h2><div className="form-grid two">
      {field('name', t('projects.nameLabel'), fields.name, (v) => change('name', v), { error: errors.name && t(errors.name), placeholder: t('projects.namePlaceholder') })}
      <div>
        <label htmlFor="project-industry" className="mb-1.5 block text-sm font-medium">{t('projects.industryLabel')} <span className="font-normal text-muted-foreground">{t('projects.required')}</span></label>
        <select id="project-industry" name="industry" value={fields.industry} onChange={(e) => change('industry', e.target.value as Industry)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-ring">{industries.map((i) => <option key={i} value={i}>{t(`industry.${i}`)}</option>)}</select>
      </div>
      </div></section><section className="form-section"><h2>{t('design.agreedScope')}</h2>
      <div>
        <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2"><label htmlFor="project-scope" className="text-sm font-medium">{t('projects.scopeLabel')} <span className="font-normal text-muted-foreground">{t('projects.required')}</span></label><Button type="button" variant="outline" className="h-8 text-xs" onClick={() => fileInput.current?.click()}>{t('projects.uploadScope')}</Button><input ref={fileInput} type="file" accept=".txt,.md,.pdf,text/plain,application/pdf" className="hidden" onChange={upload} /></div>
        {!edit && <OnboardingSlot step={1} />}
        <textarea id="project-scope" name="scope" value={fields.scope} onChange={(e) => changeScope(e.target.value)} rows={9} placeholder={t('projects.scopePlaceholder')} aria-invalid={!!errors.scope} aria-describedby={errors.scope ? 'project-scope-error' : undefined} className="w-full resize-y rounded-lg border border-input bg-background p-3 text-sm leading-relaxed focus-visible:ring-2 focus-visible:ring-ring" />
        {errors.scope && <p id="project-scope-error" className="text-xs text-outscope-text" role="alert">{t(errors.scope)}</p>}
        <p className="mt-1 text-xs text-muted-foreground">{t('projects.uploadHint')}</p>
      </div>
      </section><section className="form-section"><h2>{t('design.commercialTerms')}</h2><div className="form-grid">
      <div className="form-grid two">
        {field('startDate', t('projects.startDate'), fields.startDate, (v) => change('startDate', v), { type: 'date', error: errors.startDate && t(errors.startDate) })}
        {field('endDate', t('projects.endDate'), details.endDate, (v) => optional('endDate', v), { type: 'date', optional: true, error: attempted && endInvalid ? t('projects.endDateError') : '' })}
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div><label htmlFor="project-pricingModel" className="mb-1.5 block text-sm font-medium">{t('projects.pricingModel')} <span className="font-normal text-muted-foreground">{t('projects.required')}</span></label><select id="project-pricingModel" name="pricingModel" value={fields.pricingModel} onChange={(e) => change('pricingModel', e.target.value as PricingModel)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-ring"><option value="hourly">{t('projects.hourly')}</option><option value="fixed">{t('projects.fixed')}</option></select></div>
        <div><label htmlFor="project-currency" className="mb-1.5 block text-sm font-medium">{t('projects.currency')} <span className="font-normal text-muted-foreground">{t('projects.required')}</span></label><select id="project-currency" name="currency" value={fields.currency} onChange={(e) => change('currency', e.target.value as Currency)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-ring">{(['RUB', 'USD', 'EUR'] as const).map((c) => <option key={c}>{c}</option>)}</select></div>
      </div>
      {fields.pricingModel === 'hourly' ? field('hourlyRate', t('projects.hourlyRate'), fields.hourlyRate, (v) => change('hourlyRate', v), { type: 'number', error: errors.hourlyRate && t(errors.hourlyRate) }) : field('fixedPrice', t('projects.fixedPrice'), fields.fixedPrice, (v) => change('fixedPrice', v), { type: 'number', error: errors.fixedPrice && t(errors.fixedPrice) })}
      </div></section><section className="form-section"><h2>{t('design.clientDetails')}</h2>
      <div className="form-grid two">
        {field('clientName', t('projects.clientLabel'), details.clientName, (v) => optional('clientName', v), { optional: true, placeholder: t('projects.clientPlaceholder') })}
        {field('clientEmail', t('projects.clientEmail'), details.clientEmail, (v) => optional('clientEmail', v), { optional: true, type: 'email', error: attempted && emailInvalid ? t('errors.invalidEmail') : '' })}
      </div>
      </section>
      {uploadError && <p role="alert" className="text-sm text-outscope-text">{t(uploadError)}</p>}
      {extracting && <div role="status"><p>{t('projects.extracting')}</p><Button type="button" variant="ghost" onClick={() => { extraction.current?.abort(); extraction.current = null; setExtracting(false) }}>{t('projects.cancelExtraction')}</Button></div>}
      {uploadWarnings.map((warning) => <p role="status" key={warning.code}>{warning.code === 'pages_without_text' ? t('projects.pagesWithoutText', { pages: warning.pageNumbers.join(', ') }) : t('projects.nulRemoved')}</p>)}
      {saveError && <p role="alert" className="text-sm text-outscope-text">{t(saveError)}</p>}
      <div className="project-form-actions"><Button type="submit" disabled={saving || extracting}>{saving ? t('projects.saving') : t('projects.save')}</Button><Button type="button" variant="ghost" onClick={() => setView('projects')}>{t('projects.cancel')}</Button></div>
    </form></div>
    {project && <div className="mt-8 border-t border-border pt-5"><DeleteProjectAction project={project} disabled={saving} /></div>}
  </div>
}
