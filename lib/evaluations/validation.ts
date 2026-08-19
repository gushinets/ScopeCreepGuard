import { ERROR_CODES, type ErrorCode } from '@/lib/api/errors'
import type { EvaluationAccuracy, Verdict } from '@/lib/types'

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const ACCURACIES = new Set<EvaluationAccuracy>(['correct', 'wrong', 'debatable'])
const VERDICTS = new Set<Verdict>(['in_scope', 'borderline', 'out_of_scope'])

export type EvaluationLabelParsed =
  | {
      historyEntryId: string
      accuracy: 'correct' | 'debatable'
      aiReasoning: string
    }
  | {
      historyEntryId: string
      accuracy: 'wrong'
      humanVerdict: Verdict
      aiReasoning: string
    }

export type EvaluationParseResult =
  | { ok: true; label: EvaluationLabelParsed }
  | { ok: false; error: ErrorCode; status: 400 | 404 }

export type HumanVerdictResult =
  | { ok: true; humanVerdict: Verdict | null }
  | { ok: false; error: ErrorCode }

function hasHumanVerdictKey(body: Record<string, unknown>) {
  return Object.prototype.hasOwnProperty.call(body, 'humanVerdict')
}

export function parseEvaluationInput(
  body: Record<string, unknown>,
): EvaluationParseResult {
  if (typeof body.historyEntryId !== 'string' || !UUID_PATTERN.test(body.historyEntryId)) {
    return {
      ok: false,
      error: ERROR_CODES.evaluationHistoryNotFound,
      status: 404,
    }
  }

  if (typeof body.aiReasoning !== 'string' || body.aiReasoning.trim().length === 0) {
    return {
      ok: false,
      error: ERROR_CODES.evaluationReasoningRequired,
      status: 400,
    }
  }

  if (typeof body.accuracy !== 'string' || !ACCURACIES.has(body.accuracy as EvaluationAccuracy)) {
    return {
      ok: false,
      error: ERROR_CODES.evaluationLabelInvalid,
      status: 400,
    }
  }

  const accuracy = body.accuracy as EvaluationAccuracy
  const aiReasoning = body.aiReasoning.trim()
  const historyEntryId = body.historyEntryId
  const humanVerdictPresent = hasHumanVerdictKey(body)

  if (accuracy === 'wrong') {
    if (
      typeof body.humanVerdict !== 'string' ||
      !VERDICTS.has(body.humanVerdict as Verdict)
    ) {
      return {
        ok: false,
        error: ERROR_CODES.evaluationLabelInvalid,
        status: 400,
      }
    }
    return {
      ok: true,
      label: {
        historyEntryId,
        accuracy: 'wrong',
        humanVerdict: body.humanVerdict as Verdict,
        aiReasoning,
      },
    }
  }

  if (humanVerdictPresent) {
    return {
      ok: false,
      error: ERROR_CODES.evaluationLabelInvalid,
      status: 400,
    }
  }

  return {
    ok: true,
    label: {
      historyEntryId,
      accuracy,
      aiReasoning,
    },
  }
}

export function resolveHumanVerdict(
  parsed: EvaluationLabelParsed,
  aiVerdict: Verdict,
): HumanVerdictResult {
  if (parsed.accuracy === 'debatable') {
    return { ok: true, humanVerdict: null }
  }
  if (parsed.accuracy === 'correct') {
    return { ok: true, humanVerdict: aiVerdict }
  }
  if (parsed.humanVerdict === aiVerdict) {
    return { ok: false, error: ERROR_CODES.evaluationLabelInvalid }
  }
  return { ok: true, humanVerdict: parsed.humanVerdict }
}
