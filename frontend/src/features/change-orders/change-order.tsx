import { useEffect, useState } from 'react'
import { useLocale, useTranslations } from 'use-intl'
import { Copy, FileText } from 'lucide-react'
import { Button } from '@/shared/ui/button'
import { readProjectDetails } from '@/features/projects/contracts'
import { buildChangeOrderText, formatDocumentDate, makeChangeOrderReference, type EditableDraft } from '@/features/change-orders/model/document'
import { readChangeOrder, writeChangeOrder } from '@/features/change-orders/model/draft-storage'
import { mergeEstimate } from '@/features/change-orders/model/merge-estimate'
import { downloadChangeOrder } from './download'
import { ApiClientError } from '@/shared/api/client'
import { ERROR_CODES } from '@/shared/api/errors'
import type { AnalysisResult, Currency } from '@/shared/api/models'
import { ChangeOrderDocumentPreview } from '@/features/change-orders/change-order-document-preview'
import { documentReadiness, type ReadinessField } from '@/features/change-orders/model/readiness'
import { AgreementPdfDownload, type PdfDownload } from './agreement-pdf-download'

export function ChangeOrder({ result, projectName, projectId, historyId, userId, initialDraft, documentLanguage, refreshEstimate = false, draft: controlledDraft, onDraftChange, disabled = false, draftId, savedUnchanged = false, durableWorkflow = false, onDownloadPdf }: {
  result?: AnalysisResult
  projectName: string
  projectId: string
  historyId: string
  userId: string
  initialDraft?: EditableDraft
  documentLanguage?: string
  refreshEstimate?: boolean
  draft?: EditableDraft
  onDraftChange?: (draft: EditableDraft) => void
  disabled?: boolean
  draftId?: string | null
  savedUnchanged?: boolean
  durableWorkflow?: boolean
  onDownloadPdf?: PdfDownload
}) {
  const t = useTranslations('changeOrder')
  const locale = useLocale()
  const [original] = useState<EditableDraft>(() => {
    const createdAt = initialDraft?.createdAt ?? result?.draftCreatedAt ?? new Date().toISOString()
    return {
    ...(initialDraft ?? {} as EditableDraft),
    reference: initialDraft?.reference ?? makeChangeOrderReference(createdAt, historyId),
    createdAt,
    language: documentLanguage ?? initialDraft?.language ?? result?.clientLanguage ?? (result?.requestLanguage && result.requestLanguage !== 'other' ? result.requestLanguage : locale === 'ru' ? 'ru' : 'en'),
    changeOrderLabels: result?.changeOrderLabels ?? initialDraft?.changeOrderLabels,
    projectName: initialDraft?.projectName ?? projectName, description: initialDraft?.description ?? result?.changeOrder?.description ?? '',
    estimatedHours: initialDraft?.estimatedHours ?? result?.changeOrder?.estimatedHours?.toString() ?? '',
    additionalCost: initialDraft?.additionalCost ?? result?.changeOrder?.additionalCost ?? '',
    currency: initialDraft?.currency ?? result?.changeOrder?.currency ?? '',
    timelineImpact: initialDraft?.timelineImpact ?? result?.changeOrder?.timelineImpact ?? '',
    rationale: initialDraft?.rationale ?? result?.changeOrder?.rationale ?? '', note: initialDraft?.note ?? result?.changeOrder?.note ?? '',
    providerName: initialDraft?.providerName ?? '', clientName: initialDraft?.clientName ?? '', clientEmail: initialDraft?.clientEmail ?? '', endDate: initialDraft?.endDate ?? '', additionalTerms: initialDraft?.additionalTerms ?? '', clientApproverName: initialDraft?.clientApproverName ?? '', approvalDate: initialDraft?.approvalDate ?? '', noAdditionalCharge: initialDraft?.noAdditionalCharge ?? false,
    aiValues: initialDraft?.aiValues ?? (result ? {
      description: result.changeOrder?.description,
      estimatedHours: result.changeOrder?.estimatedHours?.toString() ?? '',
      additionalCost: result.changeOrder?.additionalCost,
      currency: result.changeOrder?.currency ?? '',
      timelineImpact: result.changeOrder?.timelineImpact,
      rationale: result.changeOrder?.rationale ?? '',
      note: result.changeOrder?.note,
    } : undefined),
  }})
  const [localDraft, setLocalDraft] = useState<EditableDraft>(() => {
    if (controlledDraft) return controlledDraft
    const saved = readChangeOrder(userId, projectId, historyId, locale === 'ru' ? 'ru' : 'en')
    if (saved) return refreshEstimate && result ? mergeEstimate(saved, original) : { ...original, ...saved, reference: saved.reference ?? original.reference }
    return { ...original, ...readProjectDetails(userId, projectId) }
  })
  const draft = controlledDraft ?? localDraft
  const readiness = documentReadiness(draft)
  const [status, setStatus] = useState<'copied' | 'error' | ''>('')

  useEffect(() => {
    if (!controlledDraft) writeChangeOrder(userId, projectId, historyId, draft)
  }, [userId, projectId, historyId, draft, controlledDraft])

  function set<K extends keyof EditableDraft>(key: K, value: EditableDraft[K]) {
    if (onDraftChange) onDraftChange({ ...draft, [key]: value })
    else setLocalDraft((current) => ({ ...current, [key]: value }))
    setStatus('')
  }

  function changeCurrency(next: Currency | '') {
    set('currency', next)
  }

  function field(key: keyof EditableDraft, label: string, rows = 1) {
    const value = draft[key] as string
    const proposed = draft.aiValues?.[key as keyof NonNullable<EditableDraft['aiValues']>]
    const changed = proposed !== undefined && value !== proposed
    const issue = readiness[key as ReadinessField]
    return <div key={key}>
      <label htmlFor={`co-${key}`} className="mb-1 block text-xs font-medium text-muted-foreground">{label} {proposed !== undefined ? <span className="font-normal">{changed ? t('edited') : t('aiProposal')}</span> : !['providerName', 'clientName', 'description', 'estimatedHours', 'additionalCost', 'timelineImpact'].includes(key) && <span className="font-normal">{t('optional')}</span>}</label>
      {rows > 1 ? <textarea id={`co-${key}`} aria-invalid={!!issue} aria-describedby={issue ? `co-${key}-guidance` : undefined} rows={rows} disabled={disabled} value={value} onChange={(e) => set(key, e.target.value)} className="w-full resize-y rounded-lg border border-input bg-background p-2.5 text-sm focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40" /> :
        <input id={`co-${key}`} aria-invalid={!!issue} aria-describedby={issue ? `co-${key}-guidance` : undefined} disabled={disabled} value={value} onChange={(e) => set(key, e.target.value)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40" />}
      {issue && <p id={`co-${key}-guidance`} className="mt-1 text-xs text-amber-700 dark:text-amber-300">{t(`readiness.${issue}`, { field: label })}</p>}
    </div>
  }

  async function copy() {
    try { await navigator.clipboard.writeText(buildChangeOrderText(draft)); setStatus('copied') }
    catch { setStatus('error') }
  }

  const downloadPdf: PdfDownload = signal => {
    if (durableWorkflow) {
      if (!onDownloadPdf) return Promise.reject(new ApiClientError(ERROR_CODES.pdfExportFailed, 0))
      return onDownloadPdf(signal)
    }
    return downloadChangeOrder({ draft, projectId, draftId, savedUnchanged }, signal)
  }

  return <section aria-labelledby="change-order-heading" className="agreement-workspace">
    <div className="flex items-start justify-between gap-3"><div className="flex items-center gap-2"><FileText className="size-4 text-muted-foreground" aria-hidden="true" /><h3 id="change-order-heading" className="text-sm font-semibold">{t('heading')}</h3><span className="rounded-md bg-muted px-2 py-0.5 text-xs font-semibold">{t('draft')}</span></div><time className="text-xs text-muted-foreground" dateTime={draft.createdAt}>{formatDocumentDate(draft.createdAt, draft.language)}</time></div>
    <p className="mt-2 text-sm font-medium">{draft.projectName}</p>
    {Object.keys(readiness).length > 0 && <p role="status" className="mt-3 text-sm text-amber-700 dark:text-amber-300">{t('readiness.help')}</p>}
    <div className="agreement-editor-layout"><div className="agreement-fields"><div className="mt-4 grid gap-3">
      {field('description', t('descriptionLabel'), 3)}
      <div className="grid gap-3 sm:grid-cols-2">{field('estimatedHours', t('hoursLabel'))}{!draft.noAdditionalCharge && field('additionalCost', t('costLabel'))}</div>
      <label className="flex items-start gap-2 rounded-lg border border-border bg-muted/30 p-3 text-sm"><input type="checkbox" disabled={disabled} checked={draft.noAdditionalCharge} onChange={(event) => set('noAdditionalCharge', event.target.checked)} className="mt-0.5 size-4" /><span><span className="font-medium">{t('noAdditionalCharge')}</span><span className="mt-0.5 block text-xs text-muted-foreground">{t('noAdditionalChargeHint')}</span></span></label>
      <div><label htmlFor="co-currency" className="mb-1 block text-xs font-medium text-muted-foreground">{t('currencyLabel')} {draft.aiValues?.currency !== undefined && <span className="font-normal">{draft.currency === draft.aiValues.currency ? t('aiProposal') : t('edited')}</span>}</label><select id="co-currency" disabled={disabled} value={draft.currency} onChange={(e) => changeCurrency(e.target.value as Currency | '')} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-ring"><option value="">{t('noCurrency')}</option>{(['RUB', 'USD', 'EUR'] as const).map((currency) => <option key={currency}>{currency}</option>)}</select></div>
      {readiness.currency && <p className="text-xs text-amber-700 dark:text-amber-300">{t('readiness.required', { field: t('currencyLabel') })}</p>}
      {field('timelineImpact', t('timelineLabel'), 2)}
    </div>
    <details className="mt-4 rounded-lg border border-border px-3 py-2"><summary className="cursor-pointer text-sm font-medium focus-visible:ring-2 focus-visible:ring-ring">{t('additionalParameters')}</summary><div className="mt-3 grid gap-3">{field('rationale', t('rationaleLabel'), 2)}{field('note', t('noteLabel'), 2)}{field('additionalTerms', t('additionalTerms'), 2)}<div className="grid gap-3 sm:grid-cols-2">{field('providerName', t('providerName'))}{field('clientName', t('clientName'))}{field('clientEmail', t('clientEmail'))}{field('endDate', t('endDate'))}{field('clientApproverName', t('approvedBy'))}{field('approvalDate', t('approvalDate'))}</div></div></details>
    </div><div className="agreement-preview"><h3 className="section-title">{t('preview')}</h3><ChangeOrderDocumentPreview draft={draft} /></div></div>
    <div className="mt-4 flex flex-wrap gap-2"><Button type="button" variant="outline" onClick={() => void copy()}><Copy aria-hidden="true" />{t('copy')}</Button><AgreementPdfDownload language={draft.language} disabled={disabled} download={downloadPdf} /></div>
    {status && <p role="status" className="mt-2 text-xs text-muted-foreground">{t(status)}</p>}
  </section>
}
