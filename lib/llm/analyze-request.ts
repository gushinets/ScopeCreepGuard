import { ERROR_CODES, type ErrorCode } from '@/lib/api/errors'

export const ANALYSIS_INPUT_MAX_CHARS = 100_000

export function parseAnalyzeBody(body: Record<string, unknown>): {
  ok: true
  projectId: string
  request: string
} | { ok: false; error: ErrorCode } {
  if (typeof body.projectId !== 'string' || body.projectId.trim().length === 0) {
    return { ok: false, error: ERROR_CODES.requestBodyInvalid }
  }
  if (typeof body.request !== 'string' || body.request.trim().length === 0) {
    return { ok: false, error: ERROR_CODES.requestRequired }
  }
  return {
    ok: true,
    projectId: body.projectId.trim(),
    request: body.request.trim(),
  }
}
