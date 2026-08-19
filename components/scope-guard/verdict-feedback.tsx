'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { assertErrorCode, type ErrorCode } from '@/lib/api/errors'
import type { EvaluationAccuracy, Verdict } from '@/lib/types'
import { cn } from '@/lib/utils'
import { useStore } from './store'

const ACCURACY_ORDER: EvaluationAccuracy[] = ['correct', 'wrong', 'debatable']
const VERDICT_ORDER: Verdict[] = ['in_scope', 'borderline', 'out_of_scope']

const accuracyStyles: Record<EvaluationAccuracy, string> = {
  correct:
    'border-inscope-border bg-inscope-soft text-inscope-text aria-pressed:ring-2 aria-pressed:ring-inscope',
  wrong:
    'border-outscope-border bg-outscope-soft text-outscope-text aria-pressed:ring-2 aria-pressed:ring-outscope',
  debatable:
    'border-borderline-border bg-borderline-soft text-borderline-text aria-pressed:ring-2 aria-pressed:ring-borderline',
}

const accuracyPrefix: Record<EvaluationAccuracy, string> = {
  correct: '👍',
  wrong: '👎',
  debatable: '🤔',
}

export function VerdictFeedback() {
  const { currentHistoryEntryId, submitEvaluation } = useStore()
  const t = useTranslations()
  const [accuracy, setAccuracy] = useState<EvaluationAccuracy | null>(null)
  const [expectedVerdict, setExpectedVerdict] = useState<Verdict | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isSaved, setIsSaved] = useState(false)
  const [saveError, setSaveError] = useState<ErrorCode | ''>('')

  if (!currentHistoryEntryId) return null

  async function save(nextAccuracy: EvaluationAccuracy, nextExpected: Verdict | null) {
    setIsSaving(true)
    setSaveError('')
    try {
      if (nextAccuracy === 'wrong') {
        if (!nextExpected) {
          throw new Error('humanVerdict is required')
        }
        await submitEvaluation({ accuracy: 'wrong', humanVerdict: nextExpected })
      } else {
        await submitEvaluation({ accuracy: nextAccuracy })
      }
      setIsSaved(true)
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'verdict_feedback_save_failed',
          message: error instanceof Error ? error.message : 'Unknown save error',
        }),
      )
      if (!(error instanceof Error)) {
        throw new Error('Unknown save error')
      }
      setSaveError(assertErrorCode(error.message))
    } finally {
      setIsSaving(false)
    }
  }

  async function onAccuracyClick(next: EvaluationAccuracy) {
    if (isSaving) return
    const isReclickWrong = next === 'wrong' && accuracy === 'wrong'
    setAccuracy(next)
    if (!isReclickWrong) {
      setExpectedVerdict(null)
    }
    setIsSaved(false)
    if (next === 'wrong') return
    await save(next, null)
  }

  async function onExpectedChange(next: Verdict) {
    if (isSaving || accuracy !== 'wrong') return
    setExpectedVerdict(next)
    setIsSaved(false)
    await save('wrong', next)
  }

  function onChange() {
    setAccuracy(null)
    setExpectedVerdict(null)
    setIsSaved(false)
    setSaveError('')
  }

  if (isSaved) {
    if (!accuracy) {
      throw new Error('accuracy is required after save')
    }
    let savedLabel: string
    if (accuracy === 'wrong') {
      if (!expectedVerdict) {
        throw new Error('expectedVerdict is required after wrong save')
      }
      savedLabel = `${t('feedback.wrong')} → ${t(`verdict.${expectedVerdict}`)}`
    } else {
      savedLabel = t(`feedback.${accuracy}`)
    }

    return (
      <section
        aria-labelledby="feedback-heading"
        className="rounded-lg border border-border bg-card p-4"
      >
        <h3 id="feedback-heading" className="text-sm font-semibold text-foreground">
          {t('feedback.heading')}
        </h3>
        <p className="mt-2 text-sm text-foreground/80">
          {t('feedback.saved')}: {savedLabel}
        </p>
        <Button
          type="button"
          variant="link"
          className="mt-1 h-auto px-0"
          onClick={onChange}
        >
          {t('feedback.change')}
        </Button>
      </section>
    )
  }

  return (
    <section
      aria-labelledby="feedback-heading"
      className="rounded-lg border border-border bg-card p-4"
    >
      <h3 id="feedback-heading" className="text-sm font-semibold text-foreground">
        {t('feedback.heading')}
      </h3>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        {ACCURACY_ORDER.map((value) => (
          <Button
            key={value}
            type="button"
            variant="outline"
            disabled={isSaving}
            aria-pressed={accuracy === value}
            className={cn('h-9 justify-center', accuracyStyles[value])}
            onClick={() => {
              void onAccuracyClick(value)
            }}
          >
            <span aria-hidden="true">{accuracyPrefix[value]}</span>
            {t(`feedback.${value}`)}
          </Button>
        ))}
      </div>

      {accuracy === 'wrong' ? (
        <fieldset className="mt-4" disabled={isSaving}>
          <legend className="text-sm font-medium text-foreground">
            {t('feedback.expectedHeading')}
          </legend>
          <div className="mt-2 flex flex-col gap-2" role="radiogroup">
            {VERDICT_ORDER.map((value) => (
              <label
                key={value}
                className="flex items-center gap-2 text-sm text-foreground"
              >
                <input
                  type="radio"
                  name="expected-verdict"
                  value={value}
                  checked={expectedVerdict === value}
                  onClick={() => {
                    void onExpectedChange(value)
                  }}
                />
                {t(`verdict.${value}`)}
              </label>
            ))}
          </div>
        </fieldset>
      ) : null}

      {saveError ? (
        <p className="mt-3 text-sm text-outscope-text" role="alert">
          {t(saveError)}
        </p>
      ) : null}
    </section>
  )
}
