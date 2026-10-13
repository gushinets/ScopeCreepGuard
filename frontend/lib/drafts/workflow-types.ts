import type { AnalysisResult, Project } from '@/lib/types'
import type { EditableDraft } from '@/lib/change-order/document'

export interface WorkingDocument {
  version: 2
  reply: { text: string; tone: 'warm' | 'neutral' | 'firm'; language: string; generated: Record<'warm' | 'neutral' | 'firm', string> }
  changeOrder: EditableDraft | null
  estimate?: { analysisRunId: string; sourceDraftRevision: string; effectiveEndDate: string | null; commercialSignature: string; estimateValid: boolean } | null
  languageSelection?: LanguageSelection | null
}
export interface LanguageSelection { language: string | null; confidence: number | null; status: 'detected' | 'uncertain'; selectedLanguage: string; override: boolean; version: string; requestHash: string }
export interface AnalysisRun {
  id: string; projectId: string; sourceDraftId: string; sourceDraftRevision: string
  requestText: string; projectSnapshot: Project & { clientEmail?: string | null; endDate?: string | null }
  interfaceLocale: 'en' | 'ru'; resultSnapshot: AnalysisResult | null
  status: 'pending' | 'running' | 'succeeded' | 'failed' | 'cancelled'
  finishedAt: string | null
}
export interface WorkingDraft {
  id: string; projectId: string; revision: string; requestText: string
  lastAnalysisRunId: string | null; analysisIsStale: boolean
  draftDocument: WorkingDocument; analysisRun: AnalysisRun | null
  createdAt: string; updatedAt: string
}
export interface ArchivedCheck {
  id: string; projectId: string; date: string; request: string; verdict: AnalysisResult['verdict']; summary: string
  sourceKind: 'explicit' | 'legacy_unverified'; sourceDraftId: string | null; sourceDraftRevision: string | null
  checkSnapshot: { version: number; requestText?: string; projectSnapshot?: AnalysisRun['projectSnapshot']; analysis?: AnalysisResult; draftDocument?: WorkingDocument; provenance?: Record<string, boolean>; capturedDraft?: unknown }
}
export interface Agreement {
  id: string; reference: string; revision: string; status: 'finalized' | 'voided'
  contentSnapshot: { document: EditableDraft; projectSnapshot: AnalysisRun['projectSnapshot'] }
}
export interface DocumentExport {
  id: string; status: 'pending' | 'processing' | 'ready' | 'failed' | 'expired'; attemptCount: number; errorCode: string | null
}
export interface WorkingRevision { id: string; revision: string; reason: string; createdAt: string; stateSnapshot: WorkingDraft & { legacy?: unknown; importOrderingOnly?: boolean } }
