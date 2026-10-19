import { ERROR_CODES, type ErrorCode } from '@/shared/api/errors'
import { validISODate } from '@/features/projects/model/validation'
import { supportedClientLanguage } from '@/shared/i18n/client-language'

export const ANALYSIS_INPUT_MAX_CHARS = 100_000

export function parseAnalyzeBody(body: Record<string, unknown>): {
  ok: true
  projectId: string
  request: string
  endDate?: string
  documentLanguage?: string
} | { ok: false; error: ErrorCode } {
  const documentLanguage = supportedClientLanguage(body.documentLanguage)
  if (body.documentLanguage !== undefined && !documentLanguage) return { ok: false, error: ERROR_CODES.clientLanguageUnsupported }
  if (typeof body.projectId !== 'string' || body.projectId.trim().length === 0) {
    return { ok: false, error: ERROR_CODES.requestBodyInvalid }
  }
  if (typeof body.request !== 'string' || body.request.trim().length === 0) {
    return { ok: false, error: ERROR_CODES.requestRequired }
  }
  if (body.endDate !== undefined && (typeof body.endDate !== 'string' || !validISODate(body.endDate))) {
    return { ok: false, error: ERROR_CODES.requestBodyInvalid }
  }
  return {
    ok: true,
    projectId: body.projectId.trim(),
    request: body.request.trim(),
    ...(typeof body.endDate === 'string' ? { endDate: body.endDate } : {}),
    ...(documentLanguage ? { documentLanguage } : {}),
  }
}
