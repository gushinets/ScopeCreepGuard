import type { AnalysisResult, Verdict } from '@/lib/types'
import type { Locale } from '@/i18n/config'
import { normalizeLanguageTag, resolveClientLanguage } from '@/lib/client-language'
import { normalizeChangeOrderLabels } from '@/lib/change-order/labels'

const VERDICTS = new Set<Verdict>(['in_scope', 'borderline', 'out_of_scope'])

function invalid(reason: string): never {
  throw new Error(`invalid_analysis_result:${reason}`)
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string')
}

function parseConfidencePercent(value: unknown): number {
  if (
    typeof value !== 'number' ||
    !Number.isFinite(value) ||
    !Number.isInteger(value) ||
    value < 0 ||
    value > 100
  ) {
    invalid('confidence')
  }
  return value
}

function requireNonEmpty(value: unknown, reason: string): string {
  if (!isNonEmptyString(value)) invalid(reason)
  return value.trim()
}

export function parseAnalysisResult(value: unknown, locale: Locale = 'en', override?: string): AnalysisResult {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    invalid('not_object')
  }

  const raw = value as Record<string, unknown>
  const clientLanguage = resolveClientLanguage(raw.clientLanguage === undefined ? raw.requestLanguage : raw.clientLanguage, locale, override)
  const changeOrderLabels = normalizeChangeOrderLabels(raw.changeOrderLabels)
  if (!['ru', 'en', 'es'].includes(clientLanguage.split('-')[0]) && !changeOrderLabels) invalid('changeOrderLabels')
  if (override && normalizeLanguageTag(raw.clientLanguage) !== clientLanguage) invalid('clientLanguage_override')

  if (typeof raw.verdict !== 'string' || !VERDICTS.has(raw.verdict as Verdict)) {
    invalid('verdict')
  }
  const confidence = parseConfidencePercent(raw.confidence)
  const summary = requireNonEmpty(raw.summary, 'summary')
  const reasoning = requireNonEmpty(raw.reasoning, 'reasoning')
  if (!isStringArray(raw.citations)) {
    invalid('citations')
  }
  if (raw.suggestion !== undefined && typeof raw.suggestion !== 'string') {
    invalid('suggestion')
  }
  if (!raw.replies || typeof raw.replies !== 'object' || Array.isArray(raw.replies)) {
    invalid('replies')
  }
  const repliesRaw = raw.replies as Record<string, unknown>
  const replies = {
    warm: requireNonEmpty(repliesRaw.warm, 'replies.warm'),
    neutral: requireNonEmpty(repliesRaw.neutral, 'replies.neutral'),
    firm: requireNonEmpty(repliesRaw.firm, 'replies.firm'),
  }
  if (
    !raw.changeOrder ||
    typeof raw.changeOrder !== 'object' ||
    Array.isArray(raw.changeOrder)
  ) {
    invalid('changeOrder')
  }
  const co = raw.changeOrder as Record<string, unknown>
  if (raw.hasAdditionalWork !== undefined && typeof raw.hasAdditionalWork !== 'boolean') invalid('hasAdditionalWork')
  if (raw.requestLanguage !== undefined && !['ru', 'en', 'es', 'other'].includes(String(raw.requestLanguage))) invalid('requestLanguage')
  if (co.estimatedHours !== undefined && (typeof co.estimatedHours !== 'number' || !Number.isFinite(co.estimatedHours) || co.estimatedHours < 0)) invalid('changeOrder.estimatedHours')
  if (co.currency !== undefined && !['', 'RUB', 'USD', 'EUR'].includes(String(co.currency))) invalid('changeOrder.currency')
  if (co.rationale !== undefined && typeof co.rationale !== 'string') invalid('changeOrder.rationale')
  const estimateValid = raw.hasAdditionalWork === true && co.estimatedHours !== undefined && co.estimatedHours > 0 && /^\d+(?:\.\d{1,2})?$/.test(String(co.additionalCost)) && Number(co.additionalCost) > 0 && co.currency !== '' && typeof co.rationale === 'string' && co.rationale.trim().length > 0
  const changeOrder = {
    description: requireNonEmpty(co.description, 'changeOrder.description'),
    timelineImpact: requireNonEmpty(co.timelineImpact, 'changeOrder.timelineImpact'),
    additionalCost: requireNonEmpty(co.additionalCost, 'changeOrder.additionalCost'),
    note: requireNonEmpty(co.note, 'changeOrder.note'),
    ...(typeof co.estimatedHours === 'number' ? { estimatedHours: co.estimatedHours } : {}),
    ...(typeof co.currency === 'string' ? { currency: co.currency as '' | 'RUB' | 'USD' | 'EUR' } : {}),
    ...(typeof co.rationale === 'string' ? { rationale: co.rationale } : {}),
  }

  const result: AnalysisResult = {
    verdict: raw.verdict as Verdict,
    confidence,
    summary,
    reasoning,
    citations: raw.citations,
    replies,
    changeOrder,
    clientLanguage,
    ...(changeOrderLabels ? { changeOrderLabels } : {}),
    ...(typeof raw.hasAdditionalWork === 'boolean' ? { hasAdditionalWork: raw.hasAdditionalWork } : {}),
    ...(typeof raw.requestLanguage === 'string' ? { requestLanguage: raw.requestLanguage as 'ru' | 'en' | 'es' | 'other' } : {}),
    ...(typeof raw.hasAdditionalWork === 'boolean' ? { estimateValid: raw.hasAdditionalWork ? estimateValid : false } : {}),
  }

  if (typeof raw.suggestion === 'string' && raw.suggestion.trim().length > 0) {
    result.suggestion = raw.suggestion.trim()
  }

  return result
}
