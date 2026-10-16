import { expect, it } from 'vitest'
import type { EditableDraft } from './document'
import { buildChangeOrderText } from './document'
import { documentReadiness } from './readiness'

const draft: EditableDraft = {
  createdAt: '2026-10-15', language: 'en', projectName: 'Alerts', description: 'Add email alerts',
  estimatedHours: '2.5', additionalCost: '175.35', currency: 'USD', timelineImpact: '3 working days after approval',
  rationale: '', note: '', providerName: 'Studio', clientName: 'Clinic', clientEmail: '', endDate: '', additionalTerms: '', clientApproverName: '', approvalDate: '', noAdditionalCharge: false,
}

it.each(['providerName', 'clientName', 'description', 'estimatedHours', 'additionalCost', 'currency', 'timelineImpact'] as const)('identifies the missing %s and preserves the draft', field => {
  const incomplete = { ...draft, [field]: '' }
  expect(documentReadiness(incomplete)).toEqual({ [field]: 'required' })
  expect(incomplete[field]).toBe('')
  expect(buildChangeOrderText(incomplete)).toContain('Incomplete draft — complete or correct')
})

it('warns about combined omissions while keeping email and approval date optional', () => {
  expect(documentReadiness(draft)).toEqual({})
  const incomplete = { ...draft, providerName: '', clientName: '', description: '', estimatedHours: '', additionalCost: '', currency: '' as const, timelineImpact: '' }
  expect(Object.keys(documentReadiness(incomplete))).toHaveLength(7)
  const copy = buildChangeOrderText(incomplete)
  expect(copy).toContain('Provider; Client; 1. Requested change; Estimated effort; Additional fee; 3. Schedule impact')
  expect(copy).not.toContain('Client email')
})

it.each(['en', 'ru', 'es'])('marks incomplete copied material in its own language: %s', language => {
  const copy = buildChangeOrderText({ ...draft, language, description: '' })
  expect(copy).toContain({ en: 'Incomplete draft', ru: 'Неполный черновик', es: 'Borrador incompleto' }[language]!)
})

it('accepts explicit free work without a currency or amount and never copies the old price', () => {
  const free = { ...draft, noAdditionalCharge: true, currency: '' as const }
  expect(documentReadiness(free)).toEqual({})
  expect(buildChangeOrderText(free)).not.toContain('175.35')
})
