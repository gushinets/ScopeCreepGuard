import type { AnalysisResult, HistoryEntry, Tone, Verdict, Project } from '@/lib/types'
import type { EditableDraft } from '@/lib/change-order/document'
import type { ClientMaterials } from '@/lib/client-materials'
import type { ProjectDetails } from '@/lib/projects/browser-details'
import type { Locale } from '@/i18n/config'

export interface ReplyDocument {
  tone: Tone
  text: string
  generated: Record<Tone, string>
}
export interface DraftDocument {
  version: 1
  result: AnalysisResult
  clientMaterials: ClientMaterials | null
  changeOrder: EditableDraft | null
  reply: ReplyDocument
  projectDetails: ProjectDetails
}
export interface ProjectSnapshot extends Pick<Project, 'name' | 'industry' | 'scope' | 'startDate' | 'pricingModel' | 'currency' | 'hourlyRate' | 'fixedPrice'> {
  version: 1
  /** Absent on snapshots issued before project client names were persisted. */
  clientName?: string | null
  endDate: string | null
  documentLanguage: string | null
}
export interface DraftProofClaims {
  userId: string
  projectId: string
  request: string
  locale: Locale
  analysisSnapshot: AnalysisResult
  projectSnapshot: ProjectSnapshot
}
// Internal, verified server input. The browser submits a proof, never these snapshots.
export interface CreateDraftInput {
  projectId: string
  request: string
  locale: Locale
  idempotencyKey: string
  analysisSnapshot: AnalysisResult
  projectSnapshot: ProjectSnapshot
  draftDocument: DraftDocument
}
export interface SavedDraft {
  id: string
  projectId: string
  historyEntryId: string
  request: string
  createdAt: string
  updatedAt: string
  status: 'draft'
  locale: Locale
  requestLanguage: AnalysisResult['requestLanguage'] | null
  clientMaterialLanguage: string
  projectSnapshot: ProjectSnapshot | null
  analysisSnapshot: AnalysisResult
  draftDocument: DraftDocument
}
export interface DraftListItem {
  id: string
  requestPreview: string
  projectName: string
  verdict: Verdict
  createdAt: string
  updatedAt: string
}
export interface CreatedDraftResponse {
  draft: SavedDraft
  entry: HistoryEntry
}
