import { describe, expect, it } from 'vitest'
import { mergeEstimate } from './merge-estimate'
import type { EditableDraft } from './document'

const base: EditableDraft = {
  createdAt: '2026-10-05', language: 'en', projectName: 'Site', description: 'Blog',
  estimatedHours: '8', additionalCost: '800', currency: 'USD', timelineImpact: 'Two days',
  rationale: 'Extra feature', note: 'Draft', clientName: '', clientEmail: '', endDate: '',
  additionalTerms: '', providerName: '', clientApproverName: '', approvalDate: '', noAdditionalCharge: false,
  aiValues: { description: 'Blog', estimatedHours: '8', additionalCost: '800', currency: 'USD', timelineImpact: 'Two days', rationale: 'Extra feature', note: 'Draft' },
}

describe('refreshing an AI estimate', () => {
  it('updates untouched proposals while preserving user edits and deletions', () => {
    const saved = { ...base, additionalCost: '700', note: '', clientName: 'Jane' }
    const proposed: EditableDraft = { ...base, language: 'ru', estimatedHours: '12', additionalCost: '1200', currency: 'EUR', note: 'New draft', aiValues: { ...base.aiValues, estimatedHours: '12', additionalCost: '1200', currency: 'EUR', note: 'New draft' } }
    const merged = mergeEstimate(saved, proposed)
    expect(merged.estimatedHours).toBe('12')
    expect(merged.currency).toBe('USD')
    expect(merged.additionalCost).toBe('700')
    expect(merged.note).toBe('')
    expect(merged.clientName).toBe('Jane')
    expect(merged.language).toBe('ru')
    expect(merged.aiValues?.additionalCost).toBe('1200')
  })
})

it.each([
  { additionalCost: '175.35' },
  { currency: 'RUB' as const },
  { additionalCost: '175.35', currency: 'RUB' as const },
  { estimatedHours: '2.5', additionalCost: '175.35', currency: 'USD' as const },
  { noAdditionalCharge: true },
])('preserves manual amount/currency atomically across refresh and restoration: %j', edits => {
  const saved = { ...base, ...edits }
  const proposed = { ...base, estimatedHours: '8', additionalCost: '640.00', currency: 'EUR' as const, rationale: '8 hours at 80 EUR/hour', aiValues: { ...base.aiValues, estimatedHours: '8', additionalCost: '640.00', currency: 'EUR', rationale: '8 hours at 80 EUR/hour' } }
  const merged = mergeEstimate(saved, proposed)
  expect([merged.additionalCost, merged.currency]).toEqual([saved.additionalCost, saved.currency])
  expect(merged.rationale).toBe('')
  expect(merged.aiValues).toMatchObject(proposed.aiValues)
  expect(mergeEstimate(JSON.parse(JSON.stringify(merged)), proposed)).toEqual(merged)
})


it.each(['Renamed project', ''])('preserves the document title %j when regenerating from a historical project', projectName => {
  const saved = { ...base, projectName }
  const proposed = { ...base, projectName: 'Original snapshot name', estimatedHours: '12' }
  const merged = mergeEstimate(saved, proposed)
  expect(merged.projectName).toBe(projectName)
  expect(merged.estimatedHours).toBe('12')
})

it('retains manual ownership when a suggestion coincides with manual terms, then changes', () => {
  const saved = { ...base, estimatedHours: '2.5', additionalCost: '175.35' }
  const matching = { ...base, estimatedHours: '2.5', additionalCost: '175.35', aiValues: { ...base.aiValues, estimatedHours: '2.5', additionalCost: '175.35' } }
  const first = mergeEstimate(saved, matching)
  const changed = { ...base, estimatedHours: '10', additionalCost: '800', currency: 'EUR' as const, aiValues: { ...base.aiValues, estimatedHours: '10', additionalCost: '800', currency: 'EUR' } }
  const final = mergeEstimate(JSON.parse(JSON.stringify(first)), changed)
  expect([final.estimatedHours, final.additionalCost, final.currency]).toEqual(['2.5', '175.35', 'USD'])
})
