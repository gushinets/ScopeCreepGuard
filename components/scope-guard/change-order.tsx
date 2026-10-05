'use client'

import { useEffect, useState } from 'react'
import { useLocale, useTranslations } from 'next-intl'
import { Copy, Download, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { readProjectDetails } from '@/lib/projects/browser-details'
import { buildChangeOrderText, formatDocumentDate, type EditableDraft } from '@/lib/change-order/document'
import { readChangeOrder, writeChangeOrder } from '@/lib/change-order/draft-storage'
import { mergeEstimate } from '@/lib/change-order/merge-estimate'
import { createChangeOrderPdf } from '@/lib/change-order/pdf'
import { convertAmount, isExchangeRates, type ExchangeRates } from '@/lib/change-order/exchange-rates'
import type { AnalysisResult, Currency } from '@/lib/types'

export function ChangeOrder({ result, projectName, projectId, historyId, userId, initialDraft, documentLanguage, refreshEstimate = false }: {
  result?: AnalysisResult
  projectName: string
  projectId: string
  historyId: string
  userId: string
  initialDraft?: EditableDraft
  documentLanguage?: 'ru' | 'en'
  refreshEstimate?: boolean
}) {
  const t = useTranslations('changeOrder')
  const locale = useLocale()
  const [original] = useState<EditableDraft>(() => initialDraft ?? {
    createdAt: result?.draftCreatedAt ?? new Date().toISOString(),
    language: documentLanguage ?? (result?.requestLanguage === 'ru' ? 'ru' : result?.requestLanguage === 'en' ? 'en' : locale === 'ru' ? 'ru' : 'en'),
    projectName, description: result?.changeOrder.description ?? '',
    estimatedHours: result?.changeOrder.estimatedHours?.toString() ?? '',
    additionalCost: result?.changeOrder.additionalCost ?? '',
    currency: result?.changeOrder.currency ?? '',
    timelineImpact: result?.changeOrder.timelineImpact ?? '',
    rationale: result?.changeOrder.rationale ?? '', note: result?.changeOrder.note ?? '',
    clientName: '', clientEmail: '', endDate: '', additionalTerms: '', approvedBy: '', approvalDate: '',
    aiValues: result ? {
      description: result.changeOrder.description,
      estimatedHours: result.changeOrder.estimatedHours?.toString() ?? '',
      additionalCost: result.changeOrder.additionalCost,
      currency: result.changeOrder.currency ?? '',
      timelineImpact: result.changeOrder.timelineImpact,
      rationale: result.changeOrder.rationale ?? '',
      note: result.changeOrder.note,
    } : undefined,
  })
  const [draft, setDraft] = useState<EditableDraft>(() => {
    const saved = readChangeOrder(userId, projectId, historyId)
    if (saved) return refreshEstimate && result ? mergeEstimate(saved, original) : saved
    return { ...original, ...readProjectDetails(userId, projectId) }
  })
  const [status, setStatus] = useState<'copied' | 'downloaded' | 'error' | ''>('')
  const [rates, setRates] = useState<ExchangeRates | null>(null)
  const [ratesStatus, setRatesStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [rateRetry, setRateRetry] = useState(0)
  const [conversionError, setConversionError] = useState<'conversionNeedsRates' | 'conversionNeedsAmount' | ''>('')

  useEffect(() => {
    writeChangeOrder(userId, projectId, historyId, draft)
  }, [userId, projectId, historyId, draft])

  useEffect(() => {
    let active = true
    void (async () => {
      try {
        const response = await fetch('/api/exchange-rates', { cache: 'no-store' })
        if (!response.ok) throw new Error('Exchange rates unavailable')
        const payload: unknown = await response.json()
        if (!isExchangeRates(payload)) throw new Error('Invalid exchange rates')
        if (active) { setRates(payload); setRatesStatus('ready') }
      } catch {
        if (active) { setRates(null); setRatesStatus('error') }
      }
    })()
    return () => { active = false }
  }, [rateRetry])

  function set<K extends keyof EditableDraft>(key: K, value: EditableDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }))
    setStatus('')
    setConversionError('')
  }

  function changeCurrency(next: Currency | '') {
    if (next === draft.currency) return
    if (draft.currency && next && draft.additionalCost.trim()) {
      if (!rates) { setConversionError('conversionNeedsRates'); return }
      const converted = convertAmount(draft.additionalCost, draft.currency, next, rates)
      if (converted === null) { setConversionError('conversionNeedsAmount'); return }
      setDraft((current) => ({ ...current, currency: next, additionalCost: converted }))
    } else {
      setDraft((current) => ({ ...current, currency: next }))
    }
    setConversionError('')
    setStatus('')
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
      const response = await fetch('/noto-sans.ttf')
      if (!response.ok) throw new Error('font')
      const bytes = await createChangeOrderPdf(draft, new Uint8Array(await response.arrayBuffer()))
      const blob = new Blob([new Uint8Array(bytes)], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `change-order-${projectId}.pdf`
      anchor.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 10_000)
      setStatus('downloaded')
    } catch { setStatus('error') }
  }

  return <section aria-labelledby="change-order-heading" className="rounded-lg border border-border bg-card p-4">
    <div className="flex items-start justify-between gap-3"><div className="flex items-center gap-2"><FileText className="size-4 text-muted-foreground" aria-hidden="true" /><h3 id="change-order-heading" className="text-sm font-semibold">{t('heading')}</h3><span className="rounded-md bg-muted px-2 py-0.5 text-xs font-semibold">{t('draft')}</span></div><time className="text-xs text-muted-foreground" dateTime={draft.createdAt}>{formatDocumentDate(draft.createdAt, draft.language)}</time></div>
    <p className="mt-2 text-sm font-medium">{draft.projectName}</p>
    <div className="mt-4 grid gap-3">
      {field('description', t('descriptionLabel'), 3)}
      <div className="grid gap-3 sm:grid-cols-2">{field('estimatedHours', t('hoursLabel'))}{field('additionalCost', t('costLabel'))}</div>
      <div><label htmlFor="co-currency" className="mb-1 block text-xs font-medium text-muted-foreground">{t('currencyLabel')} {draft.aiValues?.currency !== undefined && <span className="font-normal">{draft.currency === draft.aiValues.currency ? t('aiProposal') : t('edited')}</span>}</label><select id="co-currency" value={draft.currency} onChange={(e) => changeCurrency(e.target.value as Currency | '')} aria-describedby={conversionError ? 'co-currency-error' : undefined} className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-ring"><option value="">{t('noCurrency')}</option>{(['RUB', 'USD', 'EUR'] as const).map((currency) => <option key={currency}>{currency}</option>)}</select>{conversionError && <p id="co-currency-error" role="alert" className="mt-1 text-xs text-outscope-text">{t(conversionError)}</p>}</div>
      {field('timelineImpact', t('timelineLabel'), 2)}
    </div>
    <aside className="mt-4 rounded-lg border border-border bg-muted/40 p-3" aria-label={t('currencyComparison')}>
      <p className="text-sm font-medium">{t('currencyComparison')}</p>
      {ratesStatus === 'loading' && <p className="mt-1 text-xs text-muted-foreground" role="status">{t('ratesLoading')}</p>}
      {ratesStatus === 'error' && <div className="mt-1 flex flex-wrap items-center gap-2"><p className="text-xs text-muted-foreground" role="status">{t('ratesUnavailable')}</p><Button type="button" variant="outline" className="h-7 text-xs" onClick={() => { setRatesStatus('loading'); setRateRetry((value) => value + 1) }}>{t('retryRates')}</Button></div>}
      {rates && draft.currency && (() => {
        const amounts = (['RUB', 'USD', 'EUR'] as const).map((currency) => ({ currency, amount: convertAmount(draft.additionalCost, draft.currency as Currency, currency, rates) }))
        if (amounts.some(({ amount }) => amount === null)) return <p className="mt-1 text-xs text-muted-foreground">{t('amountForComparison')}</p>
        return <div className="mt-2 grid gap-2 sm:grid-cols-3">{amounts.map(({ currency, amount }) => <div key={currency} className={`rounded-md border px-3 py-2 ${currency === draft.currency ? 'border-ring bg-background' : 'border-border bg-card'}`}><div className="text-xs font-medium text-muted-foreground">{currency}{currency === draft.currency ? ` · ${t('draftCurrency')}` : ''}</div><output className="mt-1 block text-sm font-semibold tabular-nums">{new Intl.NumberFormat(locale === 'ru' ? 'ru-RU' : 'en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(amount))}</output></div>)}</div>
      })()}
      {rates && <p className="mt-2 text-xs text-muted-foreground">{t('rateSource', { date: formatDocumentDate(rates.asOf, locale === 'ru' ? 'ru' : 'en') })} · <a href="https://www.cbr.ru/eng/currency_base/daily/" target="_blank" rel="noopener noreferrer" className="underline underline-offset-2 focus-visible:ring-2 focus-visible:ring-ring">{t('rateProvider')}</a></p>}
    </aside>
    <details className="mt-4 rounded-lg border border-border px-3 py-2"><summary className="cursor-pointer text-sm font-medium focus-visible:ring-2 focus-visible:ring-ring">{t('additionalParameters')}</summary><div className="mt-3 grid gap-3">{field('rationale', t('rationaleLabel'), 2)}{field('note', t('noteLabel'), 2)}{field('additionalTerms', t('additionalTerms'), 2)}<div className="grid gap-3 sm:grid-cols-2">{field('clientName', t('clientName'))}{field('clientEmail', t('clientEmail'))}{field('endDate', t('endDate'))}{field('approvedBy', t('approvedBy'))}{field('approvalDate', t('approvalDate'))}</div></div></details>
    <div className="mt-4 rounded-lg bg-muted p-3"><p className="mb-2 text-xs font-medium text-muted-foreground">{t('preview')}</p><pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed">{buildChangeOrderText(draft)}</pre></div>
    <div className="mt-4 flex flex-wrap gap-2"><Button type="button" variant="outline" onClick={() => void copy()}><Copy aria-hidden="true" />{t('copy')}</Button><Button type="button" variant="outline" onClick={() => void download()}><Download aria-hidden="true" />{t('downloadPdf')}</Button></div>
    {status && <p role="status" className="mt-2 text-xs text-muted-foreground">{t(status)}</p>}
  </section>
}
