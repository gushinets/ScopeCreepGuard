import { useEffect, useState } from 'react'
import { useLocale, useTranslations } from 'use-intl'
import { WorkflowApiError, workflowApi, type DraftEditor, type WorkflowOperations, type WorkingDraft } from '@/features/drafts'
import { ERROR_CODES, type ErrorCode } from '@/shared/api/errors'
import type { AnalysisResult, Project, EvaluationAccuracy, Verdict } from '@/shared/api/models'
import { featureContext } from '@/shared/ui/feature-context'

export function useAnalysisOperations(editor: DraftEditor, commands: WorkflowOperations, refreshProjects: () => Promise<unknown>) {
  const locale = useLocale()
  const t = useTranslations()
  const [phase, setPhase] = useState<'loading' | 'error' | null>(null)
  const [analysisError, setAnalysisError] = useState<ErrorCode | ''>('')
  const installedEditor = editor.controller.current
  useEffect(() => { setPhase(null); setAnalysisError('') }, [installedEditor])
  async function runAnalysis() {
    const current = editor.controller.current
    const run = editor.navigation.current
    setAnalysisError('')
    try {
      const saved = await editor.flush()
      if (!current || run !== editor.navigation.current || current !== editor.controller.current) return
      const edits = current.editToken
      setPhase('loading')
      const response = await commands.run<{ draft: WorkingDraft | null; analysisRun: WorkingDraft['analysisRun']; applied: boolean; historyEntryId?: string }>(`drafts/${saved.id}/analyses`, {
        expectedRevision: saved.revision, locale: locale === 'ru' ? 'ru' : 'en',
        ...(saved.draftDocument.languageSelection?.override ? { documentLanguage: saved.draftDocument.reply.language } : {}),
      })
      if (run !== editor.navigation.current || current !== editor.controller.current) return
      let applied = false
      if (!response.applied || !response.draft) {
        if (BigInt(current.confirmed.revision) <= BigInt(saved.revision)) current.markConflict(new WorkflowApiError(ERROR_CODES.draftConflict, 409))
      } else applied = editor.applyOperationResponse(current, edits, response.draft, saved.revision)
      if (applied && response.historyEntryId) editor.setHistoryId(response.historyEntryId)
      setPhase(null)
      if (response.historyEntryId) await refreshProjects()
    } catch (failure) {
      if (run !== editor.navigation.current || current !== editor.controller.current) return
      setAnalysisError(failure instanceof WorkflowApiError ? failure.code : ERROR_CODES.requestFailed); setPhase('error')
    }
  }
  async function regenerate() {
    await editor.applyAction(async saved => (await commands.run<{ draft: WorkingDraft }>(`drafts/${saved.id}/regenerate`, { expectedRevision: saved.revision })).draft)
  }
  async function changeClientLanguage(language: string) {
    const document = editor.controller.current?.local.draftDocument
    const order = document?.changeOrder
    const edited = document && (document.reply.text !== document.reply.generated[document.reply.tone] ||
      order && (['description', 'timelineImpact', 'rationale', 'note'] as const).some(field => order[field] !== order.aiValues?.[field]) || !!order?.additionalTerms)
    if (edited && !window.confirm(t('result.confirmClientLanguage'))) return true
    await editor.applyAction(async saved => (await commands.run<{ draft: WorkingDraft }>(`drafts/${saved.id}/translate`, { expectedRevision: saved.revision, language })).draft)
    return false
  }
  async function reset() {
    try { await editor.applyAction(async saved => (await commands.run<{ draft: WorkingDraft }>(`drafts/${saved.id}/clear`, { expectedRevision: saved.revision })).draft); setPhase(null); setAnalysisError('') }
    catch (failure) { editor.report(failure) }
  }
  async function submitEvaluation(feedback: { accuracy: EvaluationAccuracy; humanVerdict?: Verdict }) {
    if (!editor.snapshot?.lastAnalysisRunId) throw new Error('No analysis')
    await workflowApi(`analyses/${editor.snapshot.lastAnalysisRunId}/evaluation`, feedback)
  }
  return { phase, analysisError, runCheck: () => { void runAnalysis() }, regenerate, changeClientLanguage,
    reset: () => { void reset() }, submitEvaluation, resetStatus: () => { setPhase(null); setAnalysisError('') } }
}

export interface AnalysisValue {
  status: 'idle' | 'loading' | 'result' | 'error' | 'short_scope'; result: AnalysisResult | null
  analysisError: ErrorCode | ''; analysisProject: Project | null; analyzedRequest: string | null
  termsChanged: boolean; currentHistoryEntryId: string | null
  runCheck: () => void; regenerate: () => Promise<void>; changeClientLanguage: (language: string) => Promise<boolean>
  reset: () => void; submitEvaluation: (feedback: { accuracy: EvaluationAccuracy; humanVerdict?: Verdict }) => Promise<void>
}
export const [AnalysisContext, useAnalysis] = featureContext<AnalysisValue>('Analysis')
