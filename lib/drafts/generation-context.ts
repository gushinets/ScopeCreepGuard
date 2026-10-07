
import { isLocale, type Locale } from '@/i18n/config'
import type { Project } from '@/lib/types'
import { DraftProofError, verifyDraftProof } from './proof'

// Language/estimate regeneration uses historical inputs when called from a draft.
export async function generationProject(
  userId: string, body: Record<string, unknown>, current: Project, locale: Locale,
): Promise<Project> {
  if (body.draftId !== undefined) {
    if (typeof body.draftId !== 'string') throw new DraftProofError()
    const { loadDraftForUser } = await import('./data')
    const draft = await loadDraftForUser(body.draftId, userId)
    if (!draft || draft.projectId !== current.id || draft.request !== body.request) throw new DraftProofError()
    if (!draft.projectSnapshot) {
      // Historical scope/terms cannot be recovered. Existing replies can still
      // be translated from their saved analysis, without importing today's scope.
      return {
        ...current, name: draft.draftDocument.changeOrder?.projectName ?? '', clientName: (draft.draftDocument?.projectDetails?.clientName ?? draft.draftDocument?.changeOrder?.clientName ?? ''),
        scope: '', startDate: null, pricingModel: null, currency: null, hourlyRate: null, fixedPrice: null,
      }
    }
    return { ...current, ...draft.projectSnapshot, clientName: draft.projectSnapshot.clientName === undefined ? (draft.draftDocument?.projectDetails?.clientName ?? draft.draftDocument?.changeOrder?.clientName ?? '') : draft.projectSnapshot.clientName }
  }
  if (body.proof !== undefined) {
    const proofLocale = typeof body.locale === 'string' && isLocale(body.locale) ? body.locale : locale
    const claims = await verifyDraftProof(body.proof, {
      userId, projectId: current.id, request: String(body.request), locale: proofLocale,
    })
    return { ...current, ...claims.projectSnapshot, clientName: claims.projectSnapshot.clientName ?? '' }
  }
  return current
}
