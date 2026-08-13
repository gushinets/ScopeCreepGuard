'use client'

import { useState } from 'react'
import {
  ArrowRight,
  Info,
  LoaderCircle,
  Quote,
  ShieldQuestion,
  TriangleAlert,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { VerdictBanner } from './verdict'
import { ClientReply } from './client-reply'
import { ChangeOrder } from './change-order'
import { useStore } from './store'

export function ResultPanel() {
  const { status, result, runCheck, selectedProject } = useStore()

  if (status === 'idle') return <EmptyState />
  if (status === 'loading') return <LoadingState />
  if (status === 'error') return <ErrorState onRetry={runCheck} />
  if (status === 'short_scope') return <ShortScopeState />
  if (status === 'result' && result && selectedProject) {
    return <ResultState key={`${result.verdict}-${result.summary}`} />
  }
  return <EmptyState />
}

function PanelFrame({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-[24rem] flex-col rounded-xl border border-border bg-card/40 p-4 sm:p-6">
      {children}
    </div>
  )
}

function EmptyState() {
  return (
    <PanelFrame>
      <div className="m-auto max-w-sm text-center">
        <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-muted">
          <ShieldQuestion
            className="size-6 text-muted-foreground"
            aria-hidden="true"
          />
        </span>
        <h3 className="mt-4 text-base font-semibold text-foreground">
          Ready when you are
        </h3>
        <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground text-pretty">
          Paste the client&apos;s new request on the left and run{' '}
          <span className="font-medium text-foreground">Check scope</span>. You&apos;ll
          get a verdict, the reasoning behind it, and a ready-to-edit reply.
        </p>
      </div>
    </PanelFrame>
  )
}

function LoadingState() {
  return (
    <PanelFrame>
      <div className="m-auto flex max-w-sm flex-col items-center text-center">
        <LoaderCircle
          className="size-7 animate-spin text-foreground"
          aria-hidden="true"
        />
        <p className="mt-4 text-sm font-medium text-foreground" role="status">
          Comparing the request against your scope…
        </p>
        <div className="mt-4 w-full space-y-2" aria-hidden="true">
          <div className="h-3 w-3/4 animate-pulse rounded bg-muted" />
          <div className="h-3 w-full animate-pulse rounded bg-muted" />
          <div className="h-3 w-2/3 animate-pulse rounded bg-muted" />
        </div>
      </div>
    </PanelFrame>
  )
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <PanelFrame>
      <div className="m-auto max-w-sm text-center">
        <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-outscope-soft">
          <TriangleAlert
            className="size-6 text-outscope-text"
            aria-hidden="true"
          />
        </span>
        <h3 className="mt-4 text-base font-semibold text-foreground">
          Analysis didn&apos;t complete
        </h3>
        <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground text-pretty">
          Something went wrong while checking this request. Your scope and the
          request text are still saved — just try again.
        </p>
        <Button type="button" onClick={onRetry} className="mt-4 h-9">
          Try again
        </Button>
      </div>
    </PanelFrame>
  )
}

function ShortScopeState() {
  return (
    <PanelFrame>
      <div className="m-auto max-w-sm text-center">
        <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-borderline-soft">
          <Info className="size-6 text-borderline-text" aria-hidden="true" />
        </span>
        <h3 className="mt-4 text-base font-semibold text-foreground">
          Your scope is too short to judge
        </h3>
        <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground text-pretty">
          There isn&apos;t enough detail in the saved scope to compare this request
          reliably. Add the deliverables, revision rounds, and exclusions from your
          contract, proposal, or SOW, then check again.
        </p>
      </div>
    </PanelFrame>
  )
}

function ResultState() {
  const { result, selectedProject } = useStore()
  const [showChangeOrder, setShowChangeOrder] = useState(
    result?.verdict === 'out_of_scope',
  )

  const isOut = result?.verdict === 'out_of_scope'

  if (!result || !selectedProject) return null

  return (
    <div className="flex flex-col gap-4">
      <VerdictBanner
        verdict={result.verdict}
        confidence={result.confidence}
        summary={result.summary}
      />

      {/* Why this verdict */}
      <section
        aria-labelledby="why-heading"
        className="rounded-lg border border-border bg-card p-4"
      >
        <h3 id="why-heading" className="text-sm font-semibold text-foreground">
          Why this verdict
        </h3>
        <p className="mt-1.5 text-sm leading-relaxed text-foreground/80 text-pretty">
          {result.reasoning}
        </p>

        {result.citations.length > 0 && (
          <div className="mt-3">
            <p className="text-xs font-medium text-muted-foreground">
              From your saved scope
            </p>
            <ul className="mt-1.5 space-y-1.5">
              {result.citations.map((c, i) => (
                <li
                  key={i}
                  className="flex gap-2 rounded-md border-l-2 border-border bg-muted/60 px-3 py-1.5 text-sm text-foreground/80"
                >
                  <Quote
                    className="mt-0.5 size-3.5 shrink-0 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <span className="italic text-pretty">{c}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {result.suggestion && (
          <div className="mt-3 flex gap-2 rounded-md bg-borderline-soft px-3 py-2 text-sm text-borderline-text">
            <ArrowRight className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            <p className="leading-relaxed text-pretty">{result.suggestion}</p>
          </div>
        )}
      </section>

      {/* Verify warning */}
      <p className="flex items-center gap-2 rounded-md bg-muted px-3 py-2 text-xs leading-relaxed text-muted-foreground">
        <Info className="size-3.5 shrink-0" aria-hidden="true" />
        This is an AI-assisted assessment, not a legal or final decision. Review it
        before you reply to your client.
      </p>

      <ClientReply result={result} />

      {isOut || showChangeOrder ? (
        <ChangeOrder result={result} projectName={selectedProject.name} />
      ) : (
        <Button
          type="button"
          variant="outline"
          className="h-9 self-start"
          onClick={() => setShowChangeOrder(true)}
        >
          <TriangleAlert aria-hidden="true" />
          Draft a change order anyway
        </Button>
      )}
    </div>
  )
}
