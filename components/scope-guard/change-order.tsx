'use client'

import { useEffect, useState } from 'react'
import { useLocale, useTranslations } from 'next-intl'
import { Copy, Download, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { readProjectDetails } from '@/lib/projects/browser-details'
import { buildChangeOrderText, formatDocumentDate, makeChangeOrderReference, type EditableDraft } from '@/lib/change-order/document'
import { readChangeOrder, writeChangeOrder } from '@/lib/change-order/draft-storage'
import { mergeEstimate } from '@/lib/change-order/merge-estimate'
import { createChangeOrderPdf } from '@/lib/change-order/pdf'
import type { AnalysisResult, Currency } from '@/lib/types'
import { ChangeOrderDocumentPreview } from './change-order-document-preview'
import { supportedClientLanguage } from '@/lib/client-language'

export function ChangeOrder({ result, projectName, projectId, historyId, userId, initialDraft, documentLanguage, refreshEstimate = false }: {
  result?: AnalysisResult
  projectName: string
  projectId: string
  historyId: string
  userId: string
  initialDraft?: EditableDraft
  documentLanguage?: string
  refreshEstimate?: boolean
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
    projectName: initialDraft?.projectName ?? projectName, description: initialDraft?.description ?? result?.changeOrder.description ?? '',
    estimatedHours: initialDraft?.estimatedHours ?? result?.changeOrder.estimatedHours?.toString() ?? '',
    additionalCost: initialDraft?.additionalCost ?? result?.changeOrder.additionalCost ?? '',
    currency: initialDraft?.currency ?? result?.changeOrder.currency ?? '',
    timelineImpact: initialDraft?.timelineImpact ?? result?.changeOrder.timelineImpact ?? '',
    rationale: initialDraft?.rationale ?? result?.changeOrder.rationale ?? '', note: initialDraft?.note ?? result?.changeOrder.note ?? '',
    providerName: initialDraft?.providerName ?? '', clientName: initialDraft?.clientName ?? '', clientEmail: initialDraft?.clientEmail ?? '', endDate: initialDraft?.endDate ?? '', additionalTerms: initialDraft?.additionalTerms ?? '', clientApproverName: initialDraft?.clientApproverName ?? '', approvalDate: initialDraft?.approvalDate ?? '', noAdditionalCharge: initialDraft?.noAdditionalCharge ?? false,
    aiValues: result ? {
      description: result.changeOrder.description,
      estimatedHours: result.changeOrder.estimatedHours?.toString() ?? '',
      additionalCost: result.changeOrder.additionalCost,
      currency: result.changeOrder.currency ?? '',
      timelineImpact: result.changeOrder.timelineImpact,
      rationale: result.changeOrder.rationale ?? '',
      note: result.changeOrder.note,
    } : initialDraft?.aiValues,
  }})
  const [draft, setDraft] = useState<EditableDraft>(() => {
    const saved = readChangeOrder(userId, projectId, historyId, locale === 'ru' ? 'ru' : 'en')
    if (saved) return refreshEstimate && result ? mergeEstimate(saved, original) : { ...original, ...saved, reference: saved.reference ?? original.reference }
    return { ...original, ...readProjectDetails(userId, projectId) }
  })
  const [status, setStatus] = useState<'copied' | 'downloaded' | 'error' | 'pdfLanguageUnsupported' | ''>('')

  useEffect(() => {
    writeChangeOrder(userId, projectId, historyId, draft)
  }, [userId, projectId, historyId, draft])

  function set<K extends keyof EditableDraft>(key: K, value: EditableDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }))
    setStatus('')
  }

  function changeCurrency(next: Currency | '') {
    set('currency', next)
  }

  function field(key: keyof EditableDraft, label: string, rows = 1) {
    const value = draft[key] as string
    const proposed = draft.aiValues?.[key as keyof NonNullable<EditableDraft['aiValues']>]
    const changed = proposed !== undefined && value !== proposed
    return <div key={key}>
      <label htmlFor={`co-${key}`} className="mb-1 block text-xs font-medium text-muted-foreground">{label} {proposed !== undefined ? <span className="font-normal">{changed ? t('edited') : t('aiProposal')}</span> : <span className="font-normal">{t('optional')}</span>}</label>
      {rows > 1 ? <textarea id={`co-${key}`} rows={rows} value={value} onChange={(e) => set(key, e.target.value)} className="w-full resize-y rounded-lg border border-input bg-background p-2.5 text-sm focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40" /> :
        <input id={`co-${key}`} value={value} onChange={(e) => set(key, e.target.value)} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40" />}
    </div>
  }

  async function copy() {
    try { await navigator.clipboard.writeText(buildChangeOrderText(draft)); setStatus('copied') }
    catch { setStatus('error') }
  }

  async function download() {
    try {
      const [regularResponse, boldResponse] = await Promise.all([fetch('/noto-sans.ttf'), fetch('/noto-sans-bold.ttf')])
      if (!regularResponse.ok || !boldResponse.ok) throw new Error('font')
      const bytes = await createChangeOrderPdf(draft, new Uint8Array(await regularResponse.arrayBuffer()), new Uint8Array(await boldResponse.arrayBuffer()))
      const blob = new Blob([new Uint8Array(bytes)], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `change-order-${projectId}.pdf`
      anchor.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 10_000)
      setStatus('downloaded')
    } catch (error) { setStatus(error instanceof Error && error.message.startsWith('unsupported_pdf_') ? 'pdfLanguageUnsupported' : 'error') }
  }

  return <section aria-labelledby="change-order-heading" className="rounded-lg border border-border bg-card p-4">
    <div className="flex items-start justify-between gap-3"><div className="flex items-center gap-2"><FileText className="size-4 text-muted-foreground" aria-hidden="true" /><h3 id="change-order-heading" className="text-sm font-semibold">{t('heading')}</h3><span className="rounded-md bg-muted px-2 py-0.5 text-xs font-semibold">{t('draft')}</span></div><time className="text-xs text-muted-foreground" dateTime={draft.createdAt}>{formatDocumentDate(draft.createdAt, draft.language)}</time></div>
    <p className="mt-2 text-sm font-medium">{draft.projectName}</p>
    <div className="mt-4 grid gap-3">
      {field('description', t('descriptionLabel'), 3)}
      <div className="grid gap-3 sm:grid-cols-2">{field('estimatedHours', t('hoursLabel'))}{!draft.noAdditionalCharge && field('additionalCost', t('costLabel'))}</div>
      <label className="flex items-start gap-2 rounded-lg border border-border bg-muted/30 p-3 text-sm"><input type="checkbox" checked={draft.noAdditionalCharge} onChange={(event) => set('noAdditionalCharge', event.target.checked)} className="mt-0.5 size-4" /><span><span className="font-medium">{t('noAdditionalCharge')}</span><span className="mt-0.5 block text-xs text-muted-foreground">{t('noAdditionalChargeHint')}</span></span></label>
      <div><label htmlFor="co-currency" className="mb-1 block text-xs font-medium text-muted-foreground">{t('currencyLabel')} {draft.aiValues?.currency !== undefined && <span className="font-normal">{draft.currency === draft.aiValues.currency ? t('aiProposal') : t('edited')}</span>}</label><select id="co-currency" value={draft.currency} onChange={(e) => changeCurrency(e.target.value as Currency | '')} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-ring"><option value="">{t('noCurrency')}</option>{(['RUB', 'USD', 'EUR'] as const).map((currency) => <option key={currency}>{currency}</option>)}</select></div>
      {field('timelineImpact', t('timelineLabel'), 2)}
    </div>
    <details className="mt-4 rounded-lg border border-border px-3 py-2"><summary className="cursor-pointer text-sm font-medium focus-visible:ring-2 focus-visible:ring-ring">{t('additionalParameters')}</summary><div className="mt-3 grid gap-3">{field('rationale', t('rationaleLabel'), 2)}{field('note', t('noteLabel'), 2)}{field('additionalTerms', t('additionalTerms'), 2)}<div className="grid gap-3 sm:grid-cols-2">{field('providerName', t('providerName'))}{field('clientName', t('clientName'))}{field('clientEmail', t('clientEmail'))}{field('endDate', t('endDate'))}{field('clientApproverName', t('approvedBy'))}{field('approvalDate', t('approvalDate'))}</div></div></details>
    <div className="mt-6"><p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">{t('preview')}</p><ChangeOrderDocumentPreview draft={draft} /></div>
    {!supportedClientLanguage(draft.language) && <p role="alert" className="mt-3 text-sm">{t('pdfLanguageUnsupported')}</p>}
    <div className="mt-4 flex flex-wrap gap-2"><Button type="button" variant="outline" onClick={() => void copy()}><Copy aria-hidden="true" />{t('copy')}</Button><Button type="button" variant="outline" disabled={!supportedClientLanguage(draft.language)} onClick={() => void download()}><Download aria-hidden="true" />{t('downloadPdf')}</Button></div>
    {status && <p role="status" className="mt-2 text-xs text-muted-foreground">{t(status)}</p>}
  </section>
}
