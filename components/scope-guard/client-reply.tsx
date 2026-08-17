'use client'

import { useRef, useState } from 'react'
import { CheckCheck, Copy, RotateCcw } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { AnalysisResult, Tone } from '@/lib/types'

const TONES: Tone[] = ['warm', 'neutral', 'firm']

function toneLabelKey(tone: Tone) {
  return `reply.${tone}` as const
}

export function ClientReply({ result }: { result: AnalysisResult }) {
  const t = useTranslations()
  const [tone, setTone] = useState<Tone>('neutral')
  const [text, setText] = useState(result.replies.neutral)
  const [copied, setCopied] = useState(false)
  // Track whether the current text was user-edited so tone/regenerate is intentional.
  const lastGenerated = useRef(result.replies.neutral)

  function applyTone(next: Tone) {
    setTone(next)
    const edited = text !== lastGenerated.current
    if (edited) {
      const ok = window.confirm(t('reply.confirmReplace'))
      if (!ok) return
    }
    setText(result.replies[next])
    lastGenerated.current = result.replies[next]
  }

  function regenerate() {
    setText(result.replies[tone])
    lastGenerated.current = result.replies[tone]
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(text)
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'client_reply_clipboard_failed',
          message: error instanceof Error ? error.message : 'Unknown clipboard error',
        }),
      )
    }
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2200)
  }

  return (
    <section
      aria-labelledby="reply-heading"
      className="rounded-lg border border-border bg-card p-4"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 id="reply-heading" className="text-sm font-semibold text-foreground">
          {t('reply.heading')}
        </h3>

        <div
          role="radiogroup"
          aria-label={t('reply.toneAria')}
          className="inline-flex rounded-lg border border-border bg-muted p-0.5"
        >
          {TONES.map((toneOption) => (
            <button
              key={toneOption}
              type="button"
              role="radio"
              aria-checked={tone === toneOption}
              onClick={() => applyTone(toneOption)}
              className={cn(
                'rounded-md px-2.5 py-1 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                tone === toneOption
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {t(toneLabelKey(toneOption))}
            </button>
          ))}
        </div>
      </div>

      <label htmlFor="reply-text" className="sr-only">
        {t('reply.editableLabel')}
      </label>
      <textarea
        id="reply-text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={12}
        className="mt-3 w-full resize-y rounded-lg border border-input bg-background p-3 font-sans text-sm leading-relaxed text-foreground outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40"
      />

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button
          type="button"
          onClick={copy}
          className="h-9"
          aria-live="polite"
        >
          {copied ? (
            <>
              <CheckCheck className="text-inscope-foreground" aria-hidden="true" />
              {t('reply.copied')}
            </>
          ) : (
            <>
              <Copy aria-hidden="true" />
              {t('reply.copy')}
            </>
          )}
        </Button>
        <Button type="button" variant="outline" onClick={regenerate} className="h-9">
          <RotateCcw aria-hidden="true" />
          {t('reply.regenerate')}
        </Button>
        <p className="ml-auto text-xs text-muted-foreground">
          {t('reply.sendYourself')}
        </p>
      </div>

      {copied && (
        <p
          className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-inscope-text"
          role="status"
        >
          <CheckCheck className="size-3.5" aria-hidden="true" />
          {t('reply.copiedStatus')}
        </p>
      )}
    </section>
  )
}
