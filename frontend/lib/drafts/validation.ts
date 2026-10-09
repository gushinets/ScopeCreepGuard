import { isLocale, type Locale } from '@/i18n/config'
import { parseAnalysisResult } from '@/lib/llm/schema'
import { parseClientMaterials } from '@/lib/client-materials'
import { normalizeLanguageTag } from '@/lib/client-language'
import { normalizeChangeOrderLabels } from '@/lib/change-order/labels'
import type { EditableDraft } from '@/lib/change-order/document'
import type { AnalysisResult, Tone } from '@/lib/types'
import type { CreateDraftInput, DraftDocument, DraftProofClaims } from './types'

export const MAX_DRAFT_BYTES = 1_000_000
export function validDraftId(value: unknown): value is string {
  return typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
}
function invalid(): never { throw new Error('invalid_draft_document') }
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalid()
  return value as Record<string, unknown>
}
function text(value: unknown, empty = true, max = 100_000): string {
  if (typeof value !== 'string' || value.length > max || (!empty && !value.trim())) invalid()
  return value
}
function size(value: unknown) {
  if (new TextEncoder().encode(JSON.stringify(value)).length > MAX_DRAFT_BYTES) invalid()
}
export function parseSnapshot(value: unknown, locale: Locale): AnalysisResult {
  const raw = object(value)
  const parsed = parseAnalysisResult(raw, locale)
  if (raw.changeOrderLabels !== undefined && !normalizeChangeOrderLabels(raw.changeOrderLabels)) invalid()
  if (raw.draftCreatedAt !== undefined && (typeof raw.draftCreatedAt !== 'string' || !Number.isFinite(Date.parse(raw.draftCreatedAt)))) invalid()
  if (raw.estimateValid !== undefined && typeof raw.estimateValid !== 'boolean') invalid()
  return {
    ...parsed,
    ...(typeof raw.draftCreatedAt === 'string' ? { draftCreatedAt: raw.draftCreatedAt } : {}),
    ...(raw.commercialSignature !== undefined ? { commercialSignature: text(raw.commercialSignature) } : {}),
    ...(typeof raw.estimateValid === 'boolean' ? { estimateValid: raw.estimateValid } : {}),
  }
}
const editorTextFields = ['createdAt', 'projectName', 'description', 'estimatedHours', 'additionalCost', 'timelineImpact', 'rationale', 'note', 'providerName', 'clientName', 'clientEmail', 'endDate', 'additionalTerms', 'clientApproverName', 'approvalDate'] as const
export function parseEditableDraft(value: unknown): EditableDraft {
  const raw = object(value)
  const language = normalizeLanguageTag(raw.language)
  const labels = normalizeChangeOrderLabels(raw.changeOrderLabels)
  if (!language || (raw.changeOrderLabels !== undefined && !labels) || (!['ru', 'en', 'es'].includes(language.split('-')[0]) && !labels)) invalid()
  if (!['', 'RUB', 'USD', 'EUR'].includes(String(raw.currency)) || typeof raw.noAdditionalCharge !== 'boolean') invalid()
  const parsed = Object.fromEntries(editorTextFields.map((field) => [field, text(raw[field])]))
  if (!Number.isFinite(Date.parse(String(parsed.createdAt)))) invalid()
  let aiValues: EditableDraft['aiValues']
  if (raw.aiValues !== undefined) {
    const values = object(raw.aiValues)
    const fields = ['description', 'estimatedHours', 'additionalCost', 'currency', 'timelineImpact', 'rationale', 'note']
    if (Object.keys(values).some((key) => !fields.includes(key))) invalid()
    aiValues = Object.fromEntries(Object.entries(values).map(([key, value]) => [key, text(value)]))
  }
  return {
    ...parsed, language, currency: raw.currency, noAdditionalCharge: raw.noAdditionalCharge,
    ...(raw.reference !== undefined ? { reference: text(raw.reference) } : {}),
    ...(labels ? { changeOrderLabels: labels } : {}),
    ...(aiValues ? { aiValues } : {}),
  } as EditableDraft
}
export function parseDraftDocument(value: unknown, locale: Locale, snapshot: AnalysisResult): DraftDocument {
  size(value)
  const raw = object(value)
  if (raw.version !== 1) invalid()
  const result = parseSnapshot(raw.result, locale)
  for (const field of ['verdict', 'confidence', 'summary', 'reasoning', 'citations', 'suggestion', 'hasAdditionalWork', 'requestLanguage'] as const) {
    if (JSON.stringify(result[field]) !== JSON.stringify(snapshot[field])) invalid()
  }
  const reply = object(raw.reply)
  if (!['warm', 'neutral', 'firm'].includes(String(reply.tone))) invalid()
  const generated = object(reply.generated)
  const details = object(raw.projectDetails)
  if (raw.clientMaterials !== null && raw.clientMaterials === undefined) invalid()
  if (raw.changeOrder !== null && raw.changeOrder === undefined) invalid()
  return {
    version: 1, result,
    clientMaterials: raw.clientMaterials === null ? null : parseClientMaterials(raw.clientMaterials),
    changeOrder: raw.changeOrder === null ? null : parseEditableDraft(raw.changeOrder),
    reply: {
      tone: reply.tone as Tone, text: text(reply.text),
      generated: { warm: text(generated.warm), neutral: text(generated.neutral), firm: text(generated.firm) },
    },
    projectDetails: { clientName: text(details.clientName), clientEmail: text(details.clientEmail), endDate: text(details.endDate) },
  }
}
export function parseCreateDraftEnvelope(value: unknown) {
  size(value)
  const raw = object(value)
  if (!validDraftId(raw.projectId) || !validDraftId(raw.idempotencyKey) || typeof raw.locale !== 'string' || !isLocale(raw.locale)) invalid()
  const request = text(raw.request, false).trim()
  return {
    projectId: raw.projectId, idempotencyKey: raw.idempotencyKey, locale: raw.locale, request,
    proof: raw.proof, draftDocument: raw.draftDocument,
  }
}
export function parseCreateDraft(value: unknown, claims: DraftProofClaims): CreateDraftInput {
  const envelope = parseCreateDraftEnvelope(value)
  if (envelope.projectId !== claims.projectId || envelope.request !== claims.request || envelope.locale !== claims.locale) invalid()
  return {
    projectId: claims.projectId, request: claims.request, locale: claims.locale,
    idempotencyKey: envelope.idempotencyKey,
    analysisSnapshot: claims.analysisSnapshot, projectSnapshot: claims.projectSnapshot,
    draftDocument: parseDraftDocument(envelope.draftDocument, claims.locale, claims.analysisSnapshot),
  }
}
