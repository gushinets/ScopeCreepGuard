import type { EditableDraft } from './document'
import type { Locale } from '@/i18n/config'
import { normalizeLanguageTag } from '@/lib/client-language'
import { normalizeChangeOrderLabels } from './labels'

const key = (userId: string, projectId: string, historyId: string) => `scg:change-order:${userId}:${projectId}:${historyId}`

const text = (value: unknown): string => typeof value === 'string' ? value : ''

export function normalizeChangeOrderDraft(value: unknown, locale: Locale = 'en'): EditableDraft | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const stored = value as Record<string, unknown>
  const changeOrderLabels = normalizeChangeOrderLabels(stored.changeOrderLabels)
  const resolved = normalizeLanguageTag(stored.clientLanguage ?? stored.language) ?? locale
  const language = ['ru', 'en', 'es'].includes(resolved.split('-')[0]) || changeOrderLabels ? resolved : locale
  if (typeof stored.createdAt !== 'string' || typeof stored.projectName !== 'string' || typeof stored.description !== 'string') return null

  const currency = stored.currency === 'RUB' || stored.currency === 'USD' || stored.currency === 'EUR' ? stored.currency : ''
  const aiValues = stored.aiValues && typeof stored.aiValues === 'object' && !Array.isArray(stored.aiValues)
    ? Object.fromEntries(Object.entries(stored.aiValues).filter((entry): entry is [string, string] => typeof entry[1] === 'string'))
    : undefined

  return {
    aiValues,
    reference: typeof stored.reference === 'string' ? stored.reference : undefined,
    createdAt: stored.createdAt,
    language,
    changeOrderLabels,
    projectName: stored.projectName,
    description: stored.description,
    estimatedHours: text(stored.estimatedHours),
    additionalCost: text(stored.additionalCost),
    currency,
    timelineImpact: text(stored.timelineImpact),
    rationale: text(stored.rationale),
    note: text(stored.note),
    providerName: text(stored.providerName),
    clientName: text(stored.clientName),
    clientEmail: text(stored.clientEmail),
    endDate: text(stored.endDate),
    additionalTerms: text(stored.additionalTerms),
    clientApproverName: text(stored.clientApproverName ?? stored.approvedBy),
    approvalDate: text(stored.approvalDate),
    noAdditionalCharge: stored.noAdditionalCharge === true,
  }
}

export function readChangeOrder(userId: string, projectId: string, historyId: string, locale: Locale = 'en'): EditableDraft | null {
  try {
    const raw = localStorage.getItem(key(userId, projectId, historyId))
    if (!raw) return null
    const value: unknown = JSON.parse(raw)
    return normalizeChangeOrderDraft(value, locale)
  } catch { return null }
}

export function writeChangeOrder(userId: string, projectId: string, historyId: string, draft: EditableDraft): void {
  try { localStorage.setItem(key(userId, projectId, historyId), JSON.stringify(draft)) }
  catch { /* In-memory editing and export still work. */ }
}
