import { ArrowRight, Quote } from 'lucide-react'
import { useLocale, useTranslations } from 'use-intl'
import type { AnalysisResult } from '@/shared/api/models'
import { VerdictBanner } from '@/features/analysis/verdict'

/** Read-only analysis snapshot. Never derive assessment terms from the agreement. */
export function ScopeAssessment({ result, request }: { result: AnalysisResult; request?: string | null }) {
  const t = useTranslations()
  const locale = useLocale()
  const additionalWork = result.hasAdditionalWork ?? result.verdict === 'out_of_scope'
  // Before on-demand agreements, preliminary estimates lived in changeOrder.
  const estimate = result.estimate ?? result.changeOrder
  const hours = estimate?.estimatedHours
  const amount = estimate?.additionalCost
  const currency = estimate?.currency
  const cost = amount && Number.isFinite(Number(amount))
    ? currency
      ? new Intl.NumberFormat(locale, { style: 'currency', currency }).format(Number(amount))
      : new Intl.NumberFormat(locale).format(Number(amount))
    : null

  return <div className="flex flex-col gap-4">
    <VerdictBanner verdict={result.verdict} confidence={result.confidence} summary={result.summary} />
    <section aria-label={t('result.whyHeading')} className="rounded-lg border border-border bg-card p-4">
      {request && <div className="mb-4"><h3 className="text-sm font-semibold">{t('result.clientRequest')}</h3><p className="mt-1.5 whitespace-pre-wrap text-sm text-foreground/80">{request}</p></div>}
      <h3 className="text-sm font-semibold">{t('result.whyHeading')}</h3>
      <p className="mt-1.5 whitespace-pre-wrap text-sm leading-relaxed text-foreground/80">{result.reasoning}</p>
      {!!result.citations?.length && <div className="mt-3">
        <p className="text-xs font-medium text-muted-foreground">{t('result.fromScope')}</p>
        <ul className="mt-1.5 space-y-1.5">{result.citations.map((quote, index) => <li key={index} className="flex gap-2 rounded-md border-l-2 border-border bg-muted/60 px-3 py-1.5 text-sm text-foreground/80"><Quote className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" /><span className="italic">{quote}</span></li>)}</ul>
      </div>}
      {additionalWork && <div className="mt-4">
        <h3 className="text-sm font-semibold">{t('changeOrder.additionalWork')}</h3>
        <p className="mt-1 text-xs text-muted-foreground">{t('result.preliminaryEstimate')}</p>
        <dl className="mt-2 grid grid-cols-2 gap-2 text-sm">
          {hours !== undefined && <><dt>{t('changeOrder.hoursLabel')}</dt><dd>{new Intl.NumberFormat(locale).format(hours)}</dd></>}
          {cost !== null && <><dt>{t('changeOrder.costLabel')}</dt><dd>{cost}</dd></>}
        </dl>
      </div>}
      {result.suggestion && <div className="mt-4"><h3 className="text-sm font-semibold">{t('result.nextStep')}</h3><div className="mt-1.5 flex gap-2 rounded-md bg-borderline-soft px-3 py-2 text-sm text-borderline-text"><ArrowRight className="mt-0.5 size-4 shrink-0" aria-hidden="true" /><p className="leading-relaxed">{result.suggestion}</p></div></div>}
    </section>
  </div>
}
