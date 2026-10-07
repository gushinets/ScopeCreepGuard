import { ERROR_CODES, type ErrorCode } from '@/lib/api/errors'
import type { Currency, HistoryEntry, Industry, PricingModel, Verdict } from '@/lib/types'

const INDUSTRIES: Industry[] = ['Development', 'Design', 'Marketing']
const VERDICTS: Verdict[] = ['in_scope', 'borderline', 'out_of_scope']
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/

export interface ProjectInput {
  name: string
  client?: string | null
  industry: Industry
  scope: string
  startDate: string
  pricingModel: PricingModel
  currency: Currency
  hourlyRate: string | null
  fixedPrice: string | null
}

export type ProjectField = 'name' | 'scope' | 'industry' | 'startDate' | 'pricingModel' | 'currency' | 'hourlyRate' | 'fixedPrice'

export function projectFieldErrors(body: Record<string, unknown>): Partial<Record<ProjectField, ErrorCode>> {
  const errors: Partial<Record<ProjectField, ErrorCode>> = {}
  if (typeof body.name !== 'string' || body.name.trim().length === 0) errors.name = ERROR_CODES.projectNameRequired
  if (typeof body.scope !== 'string' || body.scope.trim().length === 0) errors.scope = ERROR_CODES.scopeRequired
  if (typeof body.industry !== 'string' || !INDUSTRIES.includes(body.industry as Industry)) errors.industry = ERROR_CODES.industryInvalid
  if (typeof body.startDate !== 'string' || !validISODate(body.startDate)) errors.startDate = ERROR_CODES.startDateInvalid
  if (body.pricingModel !== 'hourly' && body.pricingModel !== 'fixed') errors.pricingModel = ERROR_CODES.pricingModelInvalid
  if (body.currency !== 'RUB' && body.currency !== 'USD' && body.currency !== 'EUR') errors.currency = ERROR_CODES.currencyInvalid
  if (body.pricingModel === 'hourly' && !parseMoney(body.hourlyRate)) errors.hourlyRate = ERROR_CODES.hourlyRateInvalid
  if (body.pricingModel === 'fixed' && !parseMoney(body.fixedPrice)) errors.fixedPrice = ERROR_CODES.fixedPriceInvalid
  return errors
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
  if (typeof body.scope !== 'string' || body.scope.trim().length === 0) {
    return { ok: false, error: ERROR_CODES.scopeRequired }
  }
  if (typeof body.industry !== 'string' || !INDUSTRIES.includes(body.industry as Industry)) {
    return { ok: false, error: ERROR_CODES.industryInvalid }
  }
  if (typeof body.startDate !== 'string' || !validISODate(body.startDate)) {
    return { ok: false, error: ERROR_CODES.startDateInvalid }
  }
  if (body.pricingModel !== 'hourly' && body.pricingModel !== 'fixed') {
    return { ok: false, error: ERROR_CODES.pricingModelInvalid }
  }
  if (body.currency !== 'RUB' && body.currency !== 'USD' && body.currency !== 'EUR') {
    return { ok: false, error: ERROR_CODES.currencyInvalid }
  }
  if (body.clientName !== undefined && body.clientName !== null && typeof body.clientName !== 'string') return { ok: false, error: ERROR_CODES.clientInvalid }
  const price = body.pricingModel === 'hourly' ? body.hourlyRate : body.fixedPrice
  const amount = parseMoney(price)
  if (!amount) {
    return { ok: false, error: body.pricingModel === 'hourly' ? ERROR_CODES.hourlyRateInvalid : ERROR_CODES.fixedPriceInvalid }
  }

  return {
    ok: true,
    project: {
      name: body.name.trim(),
      ...(body.clientName !== undefined ? { client: typeof body.clientName === 'string' ? body.clientName.trim() : null } : {}),
      industry: body.industry as Industry,
      scope: body.scope.trim(),
      startDate: body.startDate,
      pricingModel: body.pricingModel as PricingModel,
      currency: body.currency as Currency,
      hourlyRate: body.pricingModel === 'hourly' ? amount : null,
      fixedPrice: body.pricingModel === 'fixed' ? amount : null,
    },
  }
}

export function validISODate(value: string): boolean {
  if (!ISO_DATE_PATTERN.test(value)) return false
  const date = new Date(`${value}T00:00:00.000Z`)
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value
}

function parseMoney(value: unknown): string | null {
  if (typeof value !== 'string' && typeof value !== 'number') return null
  const text = String(value).trim()
  if (!/^\d+(?:\.\d{1,2})?$/.test(text)) return null
  const parsed = Number(text)
  if (!Number.isFinite(parsed) || parsed <= 0 || parsed >= 1e12) return null
  return parsed.toFixed(2)
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
