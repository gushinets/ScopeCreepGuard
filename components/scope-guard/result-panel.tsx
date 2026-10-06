'use client'

import { supportedClientLanguage, PDF_CLIENT_LANGUAGES } from '@/lib/client-language'
import { applyClientMaterials } from '@/lib/client-materials'
import { useState } from 'react'
import {
  ArrowRight,
  Info,
  LoaderCircle,
  Quote,
  ShieldQuestion,
  TriangleAlert,
} from 'lucide-react'
import { useTranslations } from 'next-intl'
import { commercialSignature } from '@/lib/change-order/commercial-signature'
import { Button } from '@/components/ui/button'
import { VerdictBanner } from './verdict'
import { ClientReply } from './client-reply'
import { ChangeOrder } from './change-order'
import { VerdictFeedback } from './verdict-feedback'
import { useStore } from './store'

export function ResultPanel() {
  const { status, result, runCheck, selectedProject, draftSessionId } = useStore()

  if (status === 'idle') return <EmptyState />
  if (status === 'loading') return <LoadingState />
  if (status === 'error') return <ErrorState onRetry={runCheck} />
  if (status === 'short_scope') return <ShortScopeState />
  if (status === 'result' && result && selectedProject) {
    return <ResultState key={draftSessionId} />
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
  const t = useTranslations()

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
          {t('result.emptyTitle')}
        </h3>
        <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground text-pretty">
          {t('result.emptyBeforeAction')}{' '}
          <span className="font-medium text-foreground">
            {t('check.checkScope')}
          </span>
          . {t('result.emptyAfterAction')}
        </p>
      </div>
    </PanelFrame>
  )
}

function LoadingState() {
  const t = useTranslations()

  return (
    <PanelFrame>
      <div className="m-auto flex max-w-sm flex-col items-center text-center">
        <LoaderCircle
          className="size-7 animate-spin text-foreground"
          aria-hidden="true"
        />
        <p className="mt-4 text-sm font-medium text-foreground" role="status">
          {t('result.loading')}
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
  const t = useTranslations()
  const { analysisError } = useStore()

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
          {t('result.errorTitle')}
        </h3>
        <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground text-pretty">
          {analysisError ? t(analysisError) : t('result.errorDescription')}
        </p>
        <Button type="button" onClick={onRetry} className="mt-4 h-9">
          {t('result.tryAgain')}
        </Button>
      </div>
    </PanelFrame>
  )
}

function ShortScopeState() {
  const t = useTranslations()

  return (
    <PanelFrame>
      <div className="m-auto max-w-sm text-center">
        <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-borderline-soft">
          <Info className="size-6 text-borderline-text" aria-hidden="true" />
        </span>
        <h3 className="mt-4 text-base font-semibold text-foreground">
          {t('result.shortScopeTitle')}
        </h3>
        <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground text-pretty">
          {t('result.shortScopeDescription')}
        </p>
      </div>
    </PanelFrame>
  )
}

function ResultState() {
  const { result, selectedProject, currentHistoryEntryId, analyzedRequest, user, setView, createEstimate, clientMaterials, changeClientLanguage, draftDocument, currentDraftId, draftSessionId, updateReply, updateChangeOrder, saveDraft, isSavingDraft, draftError, isDraftDirty } =
    useStore()
  const t = useTranslations()
  const [showChangeOrder, setShowChangeOrder] = useState(!!currentDraftId && !!draftDocument?.changeOrder)
  const [documentLanguage, setDocumentLanguage] = useState(clientMaterials?.clientLanguage ?? result?.clientLanguage ?? '')
  const languageError = documentLanguage && !supportedClientLanguage(documentLanguage) ? t('errors.clientLanguageUnsupported') : ''
  const [generating, setGenerating] = useState(false)
  const [estimateError, setEstimateError] = useState('')
  const hasAdditionalWork = result?.verdict !== 'in_scope' && (result?.hasAdditionalWork ?? result?.verdict === 'out_of_scope')
  const termsComplete = !!selectedProject?.startDate && !!selectedProject.pricingModel && !!selectedProject.currency && !!(selectedProject.hourlyRate || selectedProject.fixedPrice)

  if (!result || !selectedProject) return null

  const material = clientMaterials ? applyClientMaterials(result, clientMaterials) : result

  const endDate = draftDocument?.changeOrder?.endDate ?? draftDocument?.projectDetails.endDate ?? ''
  const needsEstimate = !material.estimateValid || material.commercialSignature !== commercialSignature(selectedProject, endDate)

  async function openChangeOrder() {
    if (!result || !selectedProject || !termsComplete) { setView('edit_project'); return }
    if (!needsEstimate) { setShowChangeOrder(true); return }
    setGenerating(true)
    setEstimateError('')
    try {
      await createEstimate(selectedProject.id, analyzedRequest ?? '', material.clientLanguage)
      setShowChangeOrder(true)
    } catch { setEstimateError(t('result.changeOrderError')) }
    finally { setGenerating(false) }
  }

  async function applyClientLanguage() {
    const code = supportedClientLanguage(documentLanguage)
    if (!code || !selectedProject) return
    setGenerating(true)
    setEstimateError('')
    try {
      await changeClientLanguage(code)
      setDocumentLanguage(code)
    } catch { setEstimateError(t('result.clientLanguageError')) }
    finally { setGenerating(false) }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" disabled={isSavingDraft || generating} onClick={() => void saveDraft()}>
          {isSavingDraft ? t(currentDraftId ? 'drafts.saving' : 'drafts.creating') : t(currentDraftId ? 'drafts.save' : 'drafts.create')}
        </Button>
        {currentDraftId && <p role="status" className="text-xs text-muted-foreground">{t(isDraftDirty ? 'drafts.unsaved' : 'drafts.saved')}</p>}
        {!currentDraftId && <p className="text-xs text-muted-foreground">{t('drafts.temporary')}</p>}
      </div>
      {draftError && <p role="alert" className="text-sm text-outscope-text">{t(draftError)}</p>}
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
          {t('result.whyHeading')}
        </h3>
        <p className="mt-1.5 text-sm leading-relaxed text-foreground/80 text-pretty">
          {result.reasoning}
        </p>

        {result.citations.length > 0 && (
          <div className="mt-3">
            <p className="text-xs font-medium text-muted-foreground">
              {t('result.fromScope')}
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

      <VerdictFeedback key={currentHistoryEntryId ?? 'unlabeled'} />

      {/* Verify warning */}
      <p className="flex items-center gap-2 rounded-md bg-muted px-3 py-2 text-xs leading-relaxed text-muted-foreground">
        <Info className="size-3.5 shrink-0" aria-hidden="true" />
        {t('result.verifyWarning')}
      </p>

      <ClientReply
        key={material.clientLanguage}
        result={material}
        document={draftDocument?.reply}
        onDocumentChange={updateReply}
        disabled={isSavingDraft || generating}
        projectId={selectedProject.id}
        request={analyzedRequest ?? ''}
      />

      <details className="rounded-lg border border-border p-3"><summary className="cursor-pointer text-sm">{t('result.documentLanguage')}</summary>
        <p className="mt-2 text-xs text-muted-foreground">{t('result.clientLanguageHint', { language: material.clientLanguage ?? '' })}</p>
        <div className="mt-2 flex gap-2"><input id="co-document-language" aria-label={t('result.documentLanguage')} aria-invalid={!!languageError} aria-describedby="client-language-feedback" disabled={generating || isSavingDraft} list="client-languages" value={documentLanguage} onChange={(e) => setDocumentLanguage(e.target.value)} placeholder="de, pt, pt-BR..." maxLength={100} className="min-w-0 rounded-lg border border-input bg-background px-3 py-2 text-sm" />
          <datalist id="client-languages">{[...PDF_CLIENT_LANGUAGES, 'pt-BR'].map((code) => <option key={code} value={code} />)}</datalist>
          <Button type="button" variant="outline" disabled={generating || isSavingDraft || !supportedClientLanguage(documentLanguage)} onClick={() => void applyClientLanguage()}>{generating ? t('result.generatingClientMaterials') : t('result.applyClientLanguage')}</Button>
        </div>
        <p id="client-language-feedback" role={languageError ? 'alert' : undefined} className="mt-2 text-xs text-muted-foreground">{languageError || t('result.supportedClientLanguages')}</p>
      </details>
      {estimateError && <p role="alert" className="text-sm text-outscope-text">{estimateError}</p>}

      {hasAdditionalWork && showChangeOrder && needsEstimate && (
        <Button type="button" variant="outline" className="self-start" disabled={generating || isSavingDraft} onClick={() => void openChangeOrder()}>
          {generating ? t('result.generatingChangeOrder') : t('result.createChangeOrder')}
        </Button>
      )}
      {hasAdditionalWork && (showChangeOrder && (termsComplete || !!currentDraftId) && user && draftDocument?.changeOrder ? (
        <ChangeOrder result={material} projectName={selectedProject.name} projectId={selectedProject.id} historyId={currentHistoryEntryId ?? draftSessionId} userId={user.id} draft={draftDocument.changeOrder} onDraftChange={updateChangeOrder} disabled={isSavingDraft || generating} />
      ) : (
        <Button
          type="button"
          variant="outline"
          className="h-9 self-start"
          onClick={() => void openChangeOrder()}
          disabled={generating}
        >
          <TriangleAlert aria-hidden="true" />
          {generating ? t('result.generatingChangeOrder') : termsComplete ? t('result.createChangeOrder') : t('result.completeProjectTerms')}
        </Button>
      ))}
    </div>
  )
}
