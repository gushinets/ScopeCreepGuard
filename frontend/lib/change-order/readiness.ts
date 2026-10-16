import type { EditableDraft } from './document'

export type ReadinessField = 'providerName' | 'clientName' | 'description' | 'estimatedHours' | 'additionalCost' | 'currency' | 'timelineImpact'
export function documentReadiness(draft: EditableDraft): Partial<Record<ReadinessField, 'required' | 'positive'>> {
  const issues: Partial<Record<ReadinessField, 'required' | 'positive'>> = {}
  for (const field of ['providerName', 'clientName', 'description'] as const) {
    if (!draft[field].trim()) issues[field] = 'required'
  }
  for (const field of ['estimatedHours', 'additionalCost'] as const) {
    if (field === 'additionalCost' && draft.noAdditionalCharge) continue
    const value = draft[field].trim()
    if (!value) issues[field] = 'required'
    else if (!/^\d+(?:\.\d{1,2})?$/.test(value) || Number(value) <= 0 || Number(value) >= 1e12) issues[field] = 'positive'
  }
  if (!draft.noAdditionalCharge && !['USD', 'EUR', 'RUB'].includes(draft.currency)) issues.currency = 'required'
  if (!draft.timelineImpact.trim() && !draft.endDate) issues.timelineImpact = 'required'
  return issues
}

export function readinessMessage(draft: EditableDraft, labels: Record<string, string>): string {
  const keys: Record<ReadinessField, string> = { providerName: 'provider', clientName: 'client', description: 'requestedChange', estimatedHours: 'effort', additionalCost: 'fee', currency: 'fee', timelineImpact: 'scheduleImpact' }
  const names = [...new Set((Object.keys(documentReadiness(draft)) as ReadinessField[]).map(field => labels[keys[field]]))]
  if (!names.length) return ''
  const language = draft.language.split('-')[0]
  const prefix: Record<string, string> = { en: 'Incomplete draft — complete or correct', ru: 'Неполный черновик — заполните или исправьте', es: 'Borrador incompleto — completar o corregir' }
  return `${prefix[language] ?? `⚠ ${labels.status}`}: ${names.join('; ')}`
}
