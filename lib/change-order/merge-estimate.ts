import type { EditableDraft } from './document'

const proposalFields = ['description', 'estimatedHours', 'additionalCost', 'currency', 'timelineImpact', 'rationale', 'note'] as const

/** Refresh AI values while retaining every term the user has changed. */
export function mergeEstimate(saved: EditableDraft, proposed: EditableDraft): EditableDraft {
  const merged = { ...saved, language: proposed.language, changeOrderLabels: proposed.changeOrderLabels, projectName: proposed.projectName, aiValues: proposed.aiValues }
  for (const field of proposalFields) {
    if (saved.aiValues?.[field] === saved[field]) {
      merged[field] = proposed[field] as never
    }
  }
  return merged
}
