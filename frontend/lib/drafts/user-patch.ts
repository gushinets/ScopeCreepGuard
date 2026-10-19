import type { WorkingDraft } from './workflow-types'

export type UserPatch = Record<string, string | boolean>
const orderFields = ['description', 'estimatedHours', 'additionalCost', 'currency', 'timelineImpact', 'rationale', 'note', 'providerName', 'clientName', 'clientEmail', 'endDate', 'additionalTerms', 'clientApproverName', 'approvalDate', 'noAdditionalCharge'] as const
const commercial = ['additionalCost', 'currency', 'noAdditionalCharge'] as const

export function isUserPatch(value: unknown): value is UserPatch {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  const allowed = new Set(['requestText', 'reply.text', 'reply.tone', ...orderFields.map(field => `changeOrder.${field}`)])
  return Object.entries(value).every(([path, item]) => allowed.has(path) &&
    (path === 'changeOrder.noAdditionalCharge' ? typeof item === 'boolean' : typeof item === 'string'))
}

/** Capture user intent at edit time, including reverting an in-flight value. */
export function userPatch(before: WorkingDraft, after: WorkingDraft): UserPatch {
  const patch: UserPatch = {}
  if (before.requestText !== after.requestText) patch.requestText = after.requestText
  for (const field of ['text', 'tone'] as const) {
    if (before.draftDocument.reply[field] !== after.draftDocument.reply[field]) patch[`reply.${field}`] = after.draftDocument.reply[field]
  }
  const prior = before.draftDocument.changeOrder
  const next = after.draftDocument.changeOrder
  if (next) {
    for (const field of orderFields) {
      if (prior?.[field] !== next[field]) patch[`changeOrder.${field}`] = next[field]
    }
    if (commercial.some(field => `changeOrder.${field}` in patch)) {
      for (const field of commercial) patch[`changeOrder.${field}`] = next[field]
    }
  }
  return patch
}

export function applyUserPatch(draft: WorkingDraft, patch: UserPatch): WorkingDraft {
  const result = structuredClone(draft)
  for (const [path, value] of Object.entries(patch)) {
    if (path === 'requestText') result.requestText = value as string
    else {
      const [section, field] = path.split('.')
      const target = section === 'reply' ? result.draftDocument.reply : result.draftDocument.changeOrder
      if (target) Object.assign(target, { [field]: value })
    }
  }
  result.analysisIsStale ||= result.requestText !== draft.requestText
  return result
}
