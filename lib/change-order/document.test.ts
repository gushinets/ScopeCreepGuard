import { describe, expect, it } from 'vitest'
import { buildChangeOrderText, type EditableDraft } from './document'

const draft: EditableDraft = {
  createdAt: '2026-10-05T12:00:00.000Z', language: 'en', projectName: 'Website',
  description: 'Add a blog', estimatedHours: '10', additionalCost: '1200', currency: 'USD',
  timelineImpact: 'Two days', rationale: 'New feature', note: '',
  clientName: '', clientEmail: '', endDate: '', additionalTerms: '', approvedBy: '', approvalDate: '',
}

describe('change order document', () => {
  it('uses edited terms and omits absent optional details', () => {
    const text = buildChangeOrderText({ ...draft, additionalCost: '900', description: 'Add three articles' })
    expect(text).toContain('Add three articles')
    expect(text).toContain('900 USD')
    expect(text).not.toContain('1200')
    expect(text).not.toContain('[Client')
    expect(text).not.toContain('Client email:')
  })
  it('uses Russian client-facing text independently of UI language', () => {
    const text = buildChangeOrderText({ ...draft, language: 'ru' })
    expect(text).toContain('ЧЕРНОВИК')
    expect(text).toContain('Проект: Website')
  })
  it('omits deleted AI fields rather than restoring them', () => {
    const text = buildChangeOrderText({ ...draft, estimatedHours: '', timelineImpact: '' })
    expect(text).not.toContain('Estimated hours:')
    expect(text).not.toContain('Schedule impact:')
  })
})
