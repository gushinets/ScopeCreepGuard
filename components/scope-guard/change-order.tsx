'use client'

import { useState } from 'react'
import { CheckCheck, Copy, Download, FileText } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import type { AnalysisResult, ChangeOrderDraft } from '@/lib/types'

function Field({
  id,
  label,
  value,
  onChange,
  rows = 2,
}: {
  id: string
  label: string
  value: string
  onChange: (v: string) => void
  rows?: number
}) {
  return (
    <div>
      <label
        htmlFor={id}
        className="mb-1 block text-xs font-medium text-muted-foreground"
      >
        {label}
      </label>
      <textarea
        id={id}
        value={value}
        rows={rows}
        onChange={(e) => onChange(e.target.value)}
        className="w-full resize-y rounded-lg border border-input bg-background p-2.5 text-sm leading-relaxed text-foreground outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40"
      />
    </div>
  )
}

export function ChangeOrder({
  result,
  projectName,
}: {
  result: AnalysisResult
  projectName: string
}) {
  const t = useTranslations('changeOrder')
  const [draft, setDraft] = useState<ChangeOrderDraft>(result.changeOrder)
  const [copied, setCopied] = useState(false)
  const [downloaded, setDownloaded] = useState(false)

  function set<K extends keyof ChangeOrderDraft>(key: K, value: string) {
    setDraft((d) => ({ ...d, [key]: value }))
  }

  function asText() {
    return [
      `${t('draftTitle')} — ${projectName}`,
      '',
      `${t('additionalWork')}:\n${draft.description}`,
      '',
      `${t('timelineImpact')}:\n${draft.timelineImpact}`,
      '',
      `${t('additionalCost')}:\n${draft.additionalCost}`,
      '',
      `${t('note')}:\n${draft.note}`,
    ].join('\n')
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(asText())
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'change_order_clipboard_failed',
          message: error instanceof Error ? error.message : 'Unknown clipboard error',
        }),
      )
    }
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2200)
  }

  function download() {
    const blob = new Blob([asText()], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `change-order-${projectName.toLowerCase().replace(/\s+/g, '-')}.txt`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    setDownloaded(true)
    window.setTimeout(() => setDownloaded(false), 2200)
  }

  return (
    <section
      aria-labelledby="change-order-heading"
      className="rounded-lg border border-border bg-card p-4"
    >
      <div className="flex items-center gap-2">
        <FileText className="size-4 text-muted-foreground" aria-hidden="true" />
        <h3
          id="change-order-heading"
          className="text-sm font-semibold text-foreground"
        >
          {t('heading')}
        </h3>
      </div>

      <div className="mt-3 grid gap-3">
        <Field
          id="co-description"
          label={t('descriptionLabel')}
          value={draft.description}
          onChange={(v) => set('description', v)}
          rows={3}
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <Field
            id="co-timeline"
            label={t('timelineLabel')}
            value={draft.timelineImpact}
            onChange={(v) => set('timelineImpact', v)}
          />
          <Field
            id="co-cost"
            label={t('costLabel')}
            value={draft.additionalCost}
            onChange={(v) => set('additionalCost', v)}
          />
        </div>
        <Field
          id="co-note"
          label={t('noteLabel')}
          value={draft.note}
          onChange={(v) => set('note', v)}
        />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button type="button" variant="outline" onClick={copy} className="h-9">
          {copied ? (
            <>
              <CheckCheck aria-hidden="true" />
              {t('copied')}
            </>
          ) : (
            <>
              <Copy aria-hidden="true" />
              {t('copy')}
            </>
          )}
        </Button>
        <Button type="button" variant="outline" onClick={download} className="h-9">
          {downloaded ? (
            <>
              <CheckCheck aria-hidden="true" />
              {t('downloaded')}
            </>
          ) : (
            <>
              <Download aria-hidden="true" />
              {t('download')}
            </>
          )}
        </Button>
      </div>

      <p className="mt-3 rounded-md bg-muted px-3 py-2 text-xs leading-relaxed text-muted-foreground">
        {t('legalNotice')}
      </p>
    </section>
  )
}
