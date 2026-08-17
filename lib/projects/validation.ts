import { ERROR_CODES, type ErrorCode } from '@/lib/api/errors'
import type { HistoryEntry, Industry, Verdict } from '@/lib/types'

const INDUSTRIES: Industry[] = ['Development', 'Design', 'Marketing']
const VERDICTS: Verdict[] = ['in_scope', 'borderline', 'out_of_scope']
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/

export interface ProjectInput {
  name: string
  client: string | null
  industry: Industry
  scope: string
}

export type ProjectInputResult =
  | { ok: true; project: ProjectInput }
  | { ok: false; error: ErrorCode }

export type HistoryInputResult =
  | { ok: true; entry: Omit<HistoryEntry, 'id'> }
  | { ok: false; error: ErrorCode }

export function parseProjectInput(body: Record<string, unknown>): ProjectInputResult {
  if (typeof body.name !== 'string' || body.name.trim().length === 0) {
    return { ok: false, error: ERROR_CODES.projectNameRequired }
  }
  if (typeof body.scope !== 'string') {
    return { ok: false, error: ERROR_CODES.scopeRequired }
  }
  if (typeof body.industry !== 'string' || !INDUSTRIES.includes(body.industry as Industry)) {
    return { ok: false, error: ERROR_CODES.industryInvalid }
  }
  if (body.client !== undefined && body.client !== null && typeof body.client !== 'string') {
    return { ok: false, error: ERROR_CODES.clientInvalid }
  }

  const client = typeof body.client === 'string' ? body.client.trim() : ''

  return {
    ok: true,
    project: {
      name: body.name.trim(),
      client: client.length > 0 ? client : null,
      industry: body.industry as Industry,
      scope: body.scope.trim(),
    },
  }
}

export function parseHistoryInput(body: Record<string, unknown>): HistoryInputResult {
  if (typeof body.date !== 'string' || !ISO_DATE_PATTERN.test(body.date)) {
    return { ok: false, error: ERROR_CODES.historyDateInvalid }
  }
  if (typeof body.request !== 'string' || body.request.trim().length === 0) {
    return { ok: false, error: ERROR_CODES.requestRequired }
  }
  if (typeof body.verdict !== 'string' || !VERDICTS.includes(body.verdict as Verdict)) {
    return { ok: false, error: ERROR_CODES.verdictInvalid }
  }
  if (typeof body.summary !== 'string' || body.summary.trim().length === 0) {
    return { ok: false, error: ERROR_CODES.summaryRequired }
  }

  return {
    ok: true,
    entry: {
      date: body.date,
      request: body.request.trim(),
      verdict: body.verdict as Verdict,
      summary: body.summary.trim(),
    },
  }
}
