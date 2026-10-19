export const CHANGE_ORDER_LABEL_KEYS = [
  'title', 'draft', 'documentNumber', 'created', 'project', 'provider', 'client',
  'clientEmail', 'requestedChange', 'commercialTerms', 'estimatedEffort',
  'additionalFee', 'noAdditionalCharge', 'scheduleImpact', 'additionalTerms',
  'approval', 'approvedBy', 'date', 'draftFooter',
  // Ancillary document prose and units must follow the same language contract.
  'introduction', 'outsideScopeFree', 'endDate', 'rationale', 'terms', 'note', 'page', 'hours',
] as const

export type ChangeOrderLabels = Record<typeof CHANGE_ORDER_LABEL_KEYS[number], string>

export function normalizeChangeOrderLabels(value: unknown): ChangeOrderLabels | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined
  const raw = value as Record<string, unknown>
  if (!CHANGE_ORDER_LABEL_KEYS.every((key) => typeof raw[key] === 'string' && raw[key].trim().length > 0 && raw[key].length <= 1500 && !/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(raw[key]))) return undefined
  return Object.fromEntries(CHANGE_ORDER_LABEL_KEYS.map((key) => [key, (raw[key] as string).trim()])) as ChangeOrderLabels
}
