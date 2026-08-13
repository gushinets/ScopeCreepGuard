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
  | { ok: false; error: string }

export type HistoryInputResult =
  | { ok: true; entry: Omit<HistoryEntry, 'id'> }
  | { ok: false; error: string }

export function parseProjectInput(body: Record<string, unknown>): ProjectInputResult {
  if (typeof body.name !== 'string' || body.name.trim().length === 0) {
    return { ok: false, error: 'Project name is required.' }
  }
  if (typeof body.scope !== 'string') {
    return { ok: false, error: 'Scope is required.' }
  }
  if (typeof body.industry !== 'string' || !INDUSTRIES.includes(body.industry as Industry)) {
    return { ok: false, error: 'Industry is invalid.' }
  }
  if (body.client !== undefined && body.client !== null && typeof body.client !== 'string') {
    return { ok: false, error: 'Client must be a string.' }
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
    return { ok: false, error: 'History date is invalid.' }
  }
  if (typeof body.request !== 'string' || body.request.trim().length === 0) {
    return { ok: false, error: 'Request is required.' }
  }
  if (typeof body.verdict !== 'string' || !VERDICTS.includes(body.verdict as Verdict)) {
    return { ok: false, error: 'Verdict is invalid.' }
  }
  if (typeof body.summary !== 'string' || body.summary.trim().length === 0) {
    return { ok: false, error: 'Summary is required.' }
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
