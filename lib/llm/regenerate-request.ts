import { ERROR_CODES, type ErrorCode } from '@/lib/api/errors'
import type { Tone } from '@/lib/types'
import { ANALYSIS_INPUT_MAX_CHARS } from './analyze-request'

const TONES = new Set<Tone>(['warm', 'neutral', 'firm'])

export type RegenerateReplyInput = {
  projectId: string
  request: string
  tone: Tone
  previousReply: string
}

export function parseRegenerateReplyBody(
  body: Record<string, unknown>,
): { ok: true; value: RegenerateReplyInput } | { ok: false; error: ErrorCode } {
  if (typeof body.projectId !== 'string' || body.projectId.trim().length === 0) {
    return { ok: false, error: ERROR_CODES.requestBodyInvalid }
  }
  if (typeof body.request !== 'string' || body.request.trim().length === 0) {
    return { ok: false, error: ERROR_CODES.requestRequired }
  }
  if (typeof body.tone !== 'string' || !TONES.has(body.tone as Tone)) {
    return { ok: false, error: ERROR_CODES.requestBodyInvalid }
  }
  if (
    typeof body.previousReply !== 'string' ||
    body.previousReply.trim().length === 0
  ) {
    return { ok: false, error: ERROR_CODES.requestBodyInvalid }
  }

  const request = body.request.trim()
  const previousReply = body.previousReply.trim()
  if (
    request.length > ANALYSIS_INPUT_MAX_CHARS ||
    previousReply.length > ANALYSIS_INPUT_MAX_CHARS
  ) {
    return { ok: false, error: ERROR_CODES.analysisInputTooLarge }
  }

  return {
    ok: true,
    value: {
      projectId: body.projectId.trim(),
      request,
      tone: body.tone as Tone,
      previousReply,
    },
  }
}
