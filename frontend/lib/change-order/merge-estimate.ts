import type { EditableDraft } from './document'

const proposalFields = ['description', 'estimatedHours', 'additionalCost', 'currency', 'timelineImpact', 'rationale', 'note'] as const

/** Refresh AI values while retaining every term the user has changed. */
export function mergeEstimate(saved: EditableDraft, proposed: EditableDraft): EditableDraft {
  const merged = { ...saved, language: proposed.language, changeOrderLabels: proposed.changeOrderLabels, aiValues: proposed.aiValues }
  const untouched = (field: typeof proposalFields[number]) => {
    const before = saved.aiValues?.[field]
    return before !== undefined && (before === saved[field] ||
      ((field === 'estimatedHours' || field === 'additionalCost') && before !== '' && saved[field] !== '' && Number(before) === Number(saved[field])))
  }
  const manualPair = saved.aiValues?.manualPrice === 'true' || saved.noAdditionalCharge || !untouched('additionalCost') || !untouched('currency')
  const manualEffort = saved.aiValues?.manualEffort === 'true' || !untouched('estimatedHours')
  const manualRationale = saved.aiValues?.manualRationale === 'true' || (!!saved.rationale && !untouched('rationale'))
  for (const field of proposalFields) {
    if ((field === 'additionalCost' || field === 'currency') && manualPair) continue
    if (field === 'estimatedHours' && manualEffort) continue
    if (field === 'rationale' && (manualPair || manualEffort)) {
      if (!manualRationale) merged.rationale = ''
      continue
    }
    if (untouched(field)) {
      merged[field] = proposed[field] as never
    }
  }
  merged.aiValues = { ...saved.aiValues, ...proposed.aiValues,
    ...(manualPair ? { manualPrice: 'true' } : {}),
    ...(manualEffort ? { manualEffort: 'true' } : {}),
    ...(manualRationale ? { manualRationale: 'true' } : {}),
  }
  return merged
}
