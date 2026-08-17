import type { AnalysisResult, Tone, Verdict } from '@/lib/types'

const VERDICTS = new Set<Verdict>(['in_scope', 'borderline', 'out_of_scope'])
const TONES: Tone[] = ['warm', 'neutral', 'firm']

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string')
}

export function parseAnalysisResult(value: unknown): AnalysisResult {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('invalid_analysis_result')
  }

  const raw = value as Record<string, unknown>

  if (typeof raw.verdict !== 'string' || !VERDICTS.has(raw.verdict as Verdict)) {
    throw new Error('invalid_analysis_result')
  }
  if (typeof raw.confidence !== 'number' || !Number.isFinite(raw.confidence)) {
    throw new Error('invalid_analysis_result')
  }
  if (!isNonEmptyString(raw.summary) || !isNonEmptyString(raw.reasoning)) {
    throw new Error('invalid_analysis_result')
  }
  if (!isStringArray(raw.citations)) {
    throw new Error('invalid_analysis_result')
  }
  if (raw.suggestion !== undefined && typeof raw.suggestion !== 'string') {
    throw new Error('invalid_analysis_result')
  }
  if (!raw.replies || typeof raw.replies !== 'object' || Array.isArray(raw.replies)) {
    throw new Error('invalid_analysis_result')
  }
  const repliesRaw = raw.replies as Record<string, unknown>
  for (const tone of TONES) {
    if (!isNonEmptyString(repliesRaw[tone])) {
      throw new Error('invalid_analysis_result')
    }
  }
  if (
    !raw.changeOrder ||
    typeof raw.changeOrder !== 'object' ||
    Array.isArray(raw.changeOrder)
  ) {
    throw new Error('invalid_analysis_result')
  }
  const co = raw.changeOrder as Record<string, unknown>
  if (
    !isNonEmptyString(co.description) ||
    !isNonEmptyString(co.timelineImpact) ||
    !isNonEmptyString(co.additionalCost) ||
    !isNonEmptyString(co.note)
  ) {
    throw new Error('invalid_analysis_result')
  }

  const result: AnalysisResult = {
    verdict: raw.verdict as Verdict,
    confidence: raw.confidence,
    summary: raw.summary.trim(),
    reasoning: raw.reasoning.trim(),
    citations: raw.citations,
    replies: {
      warm: (repliesRaw.warm as string).trim(),
      neutral: (repliesRaw.neutral as string).trim(),
      firm: (repliesRaw.firm as string).trim(),
    },
    changeOrder: {
      description: co.description.trim(),
      timelineImpact: co.timelineImpact.trim(),
      additionalCost: co.additionalCost.trim(),
      note: co.note.trim(),
    },
  }

  if (typeof raw.suggestion === 'string' && raw.suggestion.trim().length > 0) {
    result.suggestion = raw.suggestion.trim()
  }

  return result
}
