import type { AnalysisResult } from './types'
import { supportedClientLanguage } from './client-language'
import { normalizeChangeOrderLabels, type ChangeOrderLabels } from './change-order/labels'

export const CLIENT_TEXT_FIELDS = ['description', 'timelineImpact', 'rationale', 'note'] as const
export type ClientChangeOrderText = Record<typeof CLIENT_TEXT_FIELDS[number], string>
export interface ClientMaterials {
  clientLanguage: string
  replies: AnalysisResult['replies']
  changeOrder: ClientChangeOrderText | null
  changeOrderLabels?: ChangeOrderLabels
}

export function parseClientMaterials(value: unknown, expectedLanguage?: string): ClientMaterials {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('invalid_client_materials')
  const raw = value as Record<string, unknown>
  const clientLanguage = supportedClientLanguage(raw.clientLanguage)
  if (!clientLanguage || (expectedLanguage && clientLanguage !== expectedLanguage)) throw new Error('invalid_client_materials_language')
  const text = (value: unknown, allowEmpty = false): string => {
    if (typeof value !== 'string' || value.length > 100_000 || (!allowEmpty && !value.trim())) throw new Error('invalid_client_materials_text')
    return value
  }
  const replies = raw.replies as Record<string, unknown> | undefined
  if (!replies || typeof replies !== 'object' || Array.isArray(replies)) throw new Error('invalid_client_materials_replies')
  let changeOrder: ClientChangeOrderText | null = null
  if (raw.changeOrder !== null && raw.changeOrder !== undefined) {
    if (typeof raw.changeOrder !== 'object' || Array.isArray(raw.changeOrder)) throw new Error('invalid_client_materials_change_order')
    const co = raw.changeOrder as Record<string, unknown>
    changeOrder = Object.fromEntries(CLIENT_TEXT_FIELDS.map((field) => [field, text(co[field], field === 'rationale')])) as ClientChangeOrderText
  }
  const changeOrderLabels = normalizeChangeOrderLabels(raw.changeOrderLabels)
  if (!['ru', 'en', 'es'].includes(clientLanguage.split('-')[0]) && !changeOrderLabels) throw new Error('invalid_client_materials_labels')
  return { clientLanguage, replies: { warm: text(replies.warm), neutral: text(replies.neutral), firm: text(replies.firm) }, changeOrder, ...(changeOrderLabels ? { changeOrderLabels } : {}) }
}

/** Pick fields explicitly so neither model nor stored data can change analysis or prices. */
export function applyClientMaterials(result: AnalysisResult, materials: ClientMaterials): AnalysisResult {
  return {
    ...result, clientLanguage: materials.clientLanguage, replies: materials.replies,
    changeOrderLabels: materials.changeOrderLabels,
    changeOrder: materials.changeOrder ? { ...result.changeOrder, ...Object.fromEntries(CLIENT_TEXT_FIELDS.map((field) => [field, materials.changeOrder![field]])) } : result.changeOrder,
  }
}
