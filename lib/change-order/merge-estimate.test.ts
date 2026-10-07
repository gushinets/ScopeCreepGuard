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
    expect(merged.currency).toBe('EUR')
    expect(merged.additionalCost).toBe('700')
    expect(merged.note).toBe('')
    expect(merged.clientName).toBe('Jane')
    expect(merged.language).toBe('ru')
    expect(merged.aiValues?.additionalCost).toBe('1200')
  })
})


it.each(['Renamed project', ''])('preserves the document title %j when regenerating from a historical project', projectName => {
  const saved = { ...base, projectName }
  const proposed = { ...base, projectName: 'Original snapshot name', estimatedHours: '12' }
  const merged = mergeEstimate(saved, proposed)
  expect(merged.projectName).toBe(projectName)
  expect(merged.estimatedHours).toBe('12')
})
