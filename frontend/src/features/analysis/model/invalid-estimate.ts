import type { EditableDraft } from '@/shared/api/documents'

/** Recover a zero AI proposal without replacing deliberate manual/free terms. */
export function invalidAiEstimate(order: EditableDraft | null | undefined, additional: boolean | undefined) {
  if (!order || !additional || order.noAdditionalCharge) return false
  const ai = order.aiValues
  if (!ai || ai.manualPrice === 'true' || ai.manualEffort === 'true') return false
  return (['estimatedHours', 'additionalCost'] as const).some(field => {
    const value = Number(order[field])
    return ai[field] !== undefined && order[field] !== '' && value <= 0 && value === Number(ai[field])
  })
}
