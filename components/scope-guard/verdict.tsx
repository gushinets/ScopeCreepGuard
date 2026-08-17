import { CircleCheck, CircleX, TriangleAlert } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { cn } from '@/lib/utils'
import type { Verdict } from '@/lib/types'

export const verdictIcon: Record<Verdict, typeof CircleCheck> = {
  in_scope: CircleCheck,
  borderline: TriangleAlert,
  out_of_scope: CircleX,
}

const chipStyles: Record<Verdict, string> = {
  in_scope: 'bg-inscope-soft text-inscope-text border-inscope-border',
  borderline: 'bg-borderline-soft text-borderline-text border-borderline-border',
  out_of_scope: 'bg-outscope-soft text-outscope-text border-outscope-border',
}

function verdictLabelKey(verdict: Verdict) {
  return `verdict.${verdict}` as const
}

/** Small inline pill used in lists and history. */
export function VerdictChip({
  verdict,
  className,
}: {
  verdict: Verdict
  className?: string
}) {
  const Icon = verdictIcon[verdict]
  const t = useTranslations()

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium',
        chipStyles[verdict],
        className,
      )}
    >
      <Icon className="size-3.5" aria-hidden="true" />
      {t(verdictLabelKey(verdict))}
    </span>
  )
}

const bannerStyles: Record<Verdict, string> = {
  in_scope: 'bg-inscope-soft border-inscope-border',
  borderline: 'bg-borderline-soft border-borderline-border',
  out_of_scope: 'bg-outscope-soft border-outscope-border',
}

const iconWrapStyles: Record<Verdict, string> = {
  in_scope: 'bg-inscope text-inscope-foreground',
  borderline: 'bg-borderline text-borderline-foreground',
  out_of_scope: 'bg-outscope text-outscope-foreground',
}

const textStyles: Record<Verdict, string> = {
  in_scope: 'text-inscope-text',
  borderline: 'text-borderline-text',
  out_of_scope: 'text-outscope-text',
}

/** Large prominent status banner shown at the top of a result. */
export function VerdictBanner({
  verdict,
  confidence,
  summary,
}: {
  verdict: Verdict
  confidence: number
  summary: string
}) {
  const Icon = verdictIcon[verdict]
  const t = useTranslations()

  return (
    <div
      className={cn('rounded-lg border p-4', bannerStyles[verdict])}
      role="status"
    >
      <div className="flex items-start gap-3">
        <span
          className={cn(
            'flex size-9 shrink-0 items-center justify-center rounded-full',
            iconWrapStyles[verdict],
          )}
        >
          <Icon className="size-5" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <h3 className={cn('text-lg font-semibold', textStyles[verdict])}>
              {t(verdictLabelKey(verdict))}
            </h3>
            <ConfidenceMeter verdict={verdict} confidence={confidence} />
          </div>
          <p className="mt-1 text-sm leading-relaxed text-foreground/80 text-pretty">
            {summary}
          </p>
        </div>
      </div>
    </div>
  )
}

function ConfidenceMeter({
  verdict,
  confidence,
}: {
  verdict: Verdict
  confidence: number
}) {
  const t = useTranslations('result')
  const barColor: Record<Verdict, string> = {
    in_scope: 'bg-inscope',
    borderline: 'bg-borderline',
    out_of_scope: 'bg-outscope',
  }
  return (
    <span className="inline-flex items-center gap-2 text-xs font-medium text-muted-foreground">
      <span className="hidden sm:inline">{t('confidence')}</span>
      <span
        className="h-1.5 w-16 overflow-hidden rounded-full bg-border"
        aria-hidden="true"
      >
        <span
          className={cn('block h-full rounded-full', barColor[verdict])}
          style={{ width: `${Math.round(confidence)}%` }}
        />
      </span>
      <span className="tabular-nums">{Math.round(confidence)}%</span>
    </span>
  )
}
