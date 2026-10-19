import { type DraftEditor, type WorkflowOperations, WorkflowApiError, type WorkingDraft } from '@/features/drafts'
import type { AnalysisResult } from '@/shared/api/models'
import { ERROR_CODES } from '@/shared/api/errors'
import { featureContext } from '@/shared/ui/feature-context'

export function useAgreementCommands(editor: DraftEditor, commands: WorkflowOperations) {
  async function createEstimate() {
    let estimate: AnalysisResult | null = null
    const applied = await editor.applyAction(async saved => {
      const response = await commands.run<{ draft: WorkingDraft | null; analysisRun: { resultSnapshot: AnalysisResult } }>(`drafts/${saved.id}/estimate`, { expectedRevision: saved.revision })
      if (!response.draft) throw new WorkflowApiError(ERROR_CODES.draftConflict, 409)
      estimate = response.analysisRun.resultSnapshot
      return response.draft
    })
    if (!applied || !estimate) throw new WorkflowApiError(ERROR_CODES.draftConflict, 409)
    return estimate
  }
  async function prepareAgreement() {
    const applied = await editor.applyAction(async saved => {
      if (saved.draftDocument.changeOrder) return saved
      return (await commands.run<{ draft: WorkingDraft }>(`drafts/${saved.id}/agreement`, { expectedRevision: saved.revision })).draft
    })
    if (!applied) throw new WorkflowApiError(ERROR_CODES.draftConflict, 409)
  }
  return { createEstimate, prepareAgreement }
}
export const [AgreementContext, useAgreements] = featureContext<ReturnType<typeof useAgreementCommands>>('Change Order')
