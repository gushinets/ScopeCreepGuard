import { describe, expect, it } from 'vitest'
import { buildChangeOrderText, createChangeOrderDocument, makeChangeOrderReference, type EditableDraft } from './document'

const draft: EditableDraft = {
  createdAt: '2026-10-05T12:00:00.000Z', language: 'en', projectName: 'Website',
  description: 'Add a blog', estimatedHours: '10', additionalCost: '1200', currency: 'USD',
  timelineImpact: 'Two days', rationale: 'New feature', note: '',
  clientName: '', clientEmail: '', endDate: '', additionalTerms: '', approvedBy: '', approvalDate: '',
}

describe('change order document', () => {
  it('builds a formal agreement structure with numbered sections and signature parties', () => {
    const document = createChangeOrderDocument({ ...draft, reference: 'CO-20261005-A1B2C3' })
    expect(document.title).toBe('CHANGE ORDER')
    expect(document.status).toBe('DRAFT')
    expect(document.reference).toBe('CO-20261005-A1B2C3')
    expect(document.sections.map((section) => section.heading)).toEqual([
      '1. Requested change',
      '2. Commercial terms',
      '3. Schedule impact',
      '4. Additional terms',
    ])
    expect(document.commercialTerms).toEqual([
      { label: 'Estimated effort', value: '10 hours' },
      { label: 'Additional fee', value: '1200 USD' },
    ])
    expect(document.signatures.map((signature) => signature.label)).toEqual(['Provider', 'Client'])
  })

  it('creates a stable human-readable document reference', () => {
    expect(makeChangeOrderReference('2026-10-05T12:00:00Z', '83810c35-b9e7-4af6-a10d-abc123')).toBe('CO-20261005-ABC123')
  })

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

  it('writes the formal section hierarchy into copied text', () => {
    const text = buildChangeOrderText({ ...draft, reference: 'CO-20261005-A1B2C3' })
    expect(text).toContain('CHANGE ORDER — DRAFT')
    expect(text).toContain('Document no.: CO-20261005-A1B2C3')
    expect(text).toContain('1. Requested change')
    expect(text).toContain('2. Commercial terms')
    expect(text).toContain('Provider:')
    expect(text).toContain('Client:')
  })
})
