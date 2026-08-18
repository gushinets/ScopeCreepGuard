import type { AnalysisResult, Verdict } from '@/lib/types'

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
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) {
    invalid('confidence')
  }

  const percent = value > 0 && value <= 1 ? value * 100 : value
  if (percent > 100) {
    invalid('confidence')
  }

  return Math.round(percent)
}

function requireNonEmpty(value: unknown, reason: string): string {
  if (!isNonEmptyString(value)) invalid(reason)
  return value.trim()
}

export function parseAnalysisResult(value: unknown): AnalysisResult {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    invalid('not_object')
  }

  const raw = value as Record<string, unknown>

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
  const changeOrder = {
    description: requireNonEmpty(co.description, 'changeOrder.description'),
    timelineImpact: requireNonEmpty(co.timelineImpact, 'changeOrder.timelineImpact'),
    additionalCost: requireNonEmpty(co.additionalCost, 'changeOrder.additionalCost'),
    note: requireNonEmpty(co.note, 'changeOrder.note'),
  }

  const result: AnalysisResult = {
    verdict: raw.verdict as Verdict,
    confidence,
    summary,
    reasoning,
    citations: raw.citations,
    replies,
    changeOrder,
  }

  if (typeof raw.suggestion === 'string' && raw.suggestion.trim().length > 0) {
    result.suggestion = raw.suggestion.trim()
  }

  return result
}
