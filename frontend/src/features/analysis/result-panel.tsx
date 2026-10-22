import { OnboardingSlot, useOnboarding } from '@/features/onboarding'
import { supportedClientLanguage, PDF_CLIENT_LANGUAGES } from '@/shared/i18n/client-language'
import { useEffect, useState } from 'react'
import {
  Info,
  LoaderCircle,
  TriangleAlert,
} from 'lucide-react'
import { useLocale, useTranslations } from 'use-intl'
import { commercialSignature } from '@/features/change-orders/contracts'
import { Button } from '@/shared/ui/button'
import { ScopeAssessment } from '@/features/analysis/scope-assessment'
import { ClientReply } from '@/features/analysis/client-reply'
import { ChangeOrder } from '@/features/change-orders'
import { VerdictFeedback } from '@/features/analysis/verdict-feedback'
import { useProjects } from '@/features/projects'
import { useDrafts } from '@/features/drafts'
import { useAnalysis } from './operations'
import { useSession } from '@/features/auth'
import { useAgreements } from '@/features/change-orders'
import { useWorkspaceNavigation } from '@/shared/ui/navigation'
import { invalidAiEstimate } from './model/invalid-estimate'

export function ResultPanel() {
  const { status, result, runCheck, analysisProject: selectedProject, draftSessionId } = { ...useProjects(), ...useDrafts(), ...useAnalysis(), ...useSession(), ...useAgreements(), ...useWorkspaceNavigation() }

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
    <div className="flex min-h-[14rem] flex-col rounded-xl border border-border bg-card/40 p-4 sm:p-6">
      {children}
    </div>
  )
}

function EmptyState() {
  const t = useTranslations()
  const { termsChanged } = useAnalysis()
  return termsChanged ? <p role="status" className="mb-4 rounded-md bg-borderline-soft p-3 text-sm">{t('projects.termsChanged')}</p> : null
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
  const { analysisError } = { ...useProjects(), ...useDrafts(), ...useAnalysis(), ...useSession(), ...useAgreements(), ...useWorkspaceNavigation() }

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
  const { result, analysisProject: selectedProject, selectedProject: currentProject, currentHistoryEntryId, analyzedRequest, user, createEstimate, prepareAgreement, downloadAgreementPdf, regenerate, changeClientLanguage, draftDocument, currentDraftId, draftSessionId, updateReply, updateChangeOrder, isSavingDraft, isDraftDirty, workflow } =
    { ...useProjects(), ...useDrafts(), ...useAnalysis(), ...useSession(), ...useAgreements(), ...useWorkspaceNavigation() }
  const t = useTranslations()
  const locale = useLocale()
  const [tab, setTab] = useState<'scope' | 'reply' | 'agreement'>('scope')
  const { setResultStep } = useOnboarding()
  useEffect(() => {
    setResultStep(tab === 'scope' ? 4 : tab === 'reply' ? 5 : 6)
    return () => setResultStep(null)
  }, [tab, setResultStep])
  const languageName = (code: string) => new Intl.DisplayNames([locale], { type: 'language' }).of(code) ?? code
  const [showChangeOrder, setShowChangeOrder] = useState(!!currentDraftId && !!draftDocument?.changeOrder)
  const [documentLanguage, setDocumentLanguage] = useState(result?.clientLanguage ?? '')
  useEffect(() => { setDocumentLanguage(result?.clientLanguage ?? '') }, [result?.clientLanguage])
  const languageError = documentLanguage && !supportedClientLanguage(documentLanguage) ? t('errors.clientLanguageUnsupported') : ''
  const [generating, setGenerating] = useState(false)
  const [estimateError, setEstimateError] = useState('')

  if (!result || !selectedProject) return null

  const material = result

  const needsEstimate = !!draftDocument?.changeOrder && (invalidAiEstimate(draftDocument.changeOrder, material.hasAdditionalWork) || !material.estimateValid || material.commercialSignature !== commercialSignature(currentProject ?? selectedProject, draftDocument.changeOrder.endDate || selectedProject.endDate || ''))

  async function refreshEstimate() {
    if (!selectedProject) return
    setGenerating(true)
    setEstimateError('')
    try { await createEstimate() }
    catch { setEstimateError(t('result.changeOrderError')) }
    finally { setGenerating(false) }
  }

  async function openChangeOrder() {
    if (!selectedProject) return
    if (draftDocument?.changeOrder) { setShowChangeOrder(true); return }
    setGenerating(true)
    setEstimateError('')
    try {
      await prepareAgreement()
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
      const cancelled = await changeClientLanguage(code)
      setDocumentLanguage(cancelled ? material.clientLanguage ?? '' : code)
    } catch { setEstimateError(t('result.clientLanguageError')) }
    finally { setGenerating(false) }
  }

  return (
    <div className="result-workspace">
      <div className="result-tabs" role="tablist" aria-label={t('result.tabsLabel')}>
        {(['scope', 'reply', 'agreement'] as const).map((name, index, tabs) => <button
          key={name} type="button" role="tab" id={`result-tab-${name}`} aria-controls={`result-panel-${name}`}
          aria-selected={tab === name} tabIndex={tab === name ? 0 : -1} data-onboarding={`tab-${name}`}
          onClick={() => setTab(name)}
          onKeyDown={event => {
            const next = event.key === 'ArrowRight' ? (index + 1) % tabs.length : event.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : null
            if (next === null) return
            event.preventDefault()
            setTab(tabs[next])
            document.getElementById(`result-tab-${tabs[next]}`)?.focus()
          }}
        >{t(`result.tab${name === 'scope' ? 'Scope' : name === 'reply' ? 'Reply' : 'Agreement'}`)}</button>)}
      </div>
      <div id="result-panel-scope" role="tabpanel" aria-labelledby="result-tab-scope" hidden={tab !== 'scope'} tabIndex={0}>
      <OnboardingSlot step={4} />
      <div className="result-content">
      <ScopeAssessment result={result} request={analyzedRequest} />
      <VerdictFeedback key={currentHistoryEntryId ?? 'unlabeled'} />
      </div></div>
      <div id="result-panel-reply" role="tabpanel" aria-labelledby="result-tab-reply" hidden={tab !== 'reply'} tabIndex={0}>
      <OnboardingSlot step={5} />
      <div className="result-content">
      <ClientReply
        key={material.clientLanguage}
        result={material}
        document={draftDocument?.reply}
        onDocumentChange={updateReply}
        onRegenerate={regenerate}
        disabled={generating || !!workflow?.archived || false}
        projectId={selectedProject.id}
        request={analyzedRequest ?? ''}
      />
      <section className="client-language-control rounded-lg bg-muted p-4">
        <label htmlFor="co-document-language" className="text-sm font-medium">{t('result.documentLanguage')}</label>
        <p className="mt-2 text-xs text-muted-foreground">{t('result.clientLanguageHint', { language: languageName(material.clientLanguage ?? 'en') })}</p>
        <div className="mt-2 flex gap-2">
          <select id="co-document-language" aria-invalid={!!languageError} aria-describedby="client-language-feedback" disabled={generating || isSavingDraft || !!workflow?.archived} value={documentLanguage} onChange={(e) => setDocumentLanguage(e.target.value)} className="min-w-0 rounded-lg border border-input bg-background px-3 py-2 text-sm">
            {[...new Set<string>([...PDF_CLIENT_LANGUAGES, 'pt-BR', ...(supportedClientLanguage(documentLanguage) ? [documentLanguage] : [])])].map(code => <option key={code} value={code}>{languageName(code)}</option>)}
          </select>
          <Button type="button" variant="outline" disabled={generating || isSavingDraft || !!workflow?.archived || !supportedClientLanguage(documentLanguage)} onClick={() => void applyClientLanguage()}>{generating ? t('result.generatingClientMaterials') : t('result.applyClientLanguage')}</Button>
        </div>
        <p id="client-language-feedback" role={languageError ? 'alert' : undefined} className="mt-2 text-xs text-muted-foreground">{languageError || t('result.supportedClientLanguages')}</p>
      </section>
      </div></div>
      <div id="result-panel-agreement" role="tabpanel" aria-labelledby="result-tab-agreement" hidden={tab !== 'agreement'} tabIndex={0}>
      <OnboardingSlot step={6} />
      <div className="result-content">
      {needsEstimate && <Button type="button" variant="outline" className="self-start" disabled={generating || !!workflow?.archived} onClick={() => void refreshEstimate()}>{generating ? t('result.generatingChangeOrder') : t('result.refreshEstimate')}</Button>}
      {showChangeOrder && user && draftDocument?.changeOrder ? (
        <ChangeOrder result={material} projectName={selectedProject.name} projectId={selectedProject.id} historyId={currentHistoryEntryId ?? draftSessionId} userId={user.id} draft={draftDocument.changeOrder} onDraftChange={updateChangeOrder} disabled={generating || !!workflow?.archived || false} draftId={currentDraftId} savedUnchanged={!isDraftDirty} durableWorkflow onDownloadPdf={downloadAgreementPdf} />
      ) : (
        <Button type="button" variant="outline" className="h-9 self-start" onClick={() => void openChangeOrder()} disabled={generating || !!workflow?.archived}>
          {generating ? t('result.generatingChangeOrder') : t('result.prepareAgreement')}
        </Button>
      )}
      </div></div>
      {estimateError && <p role="alert" className="mt-4 text-sm text-outscope-text">{estimateError}</p>}
    </div>
  )
}
