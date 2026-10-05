import { describe, expect, it } from 'vitest'
import { projectAnalysisInputsChanged } from './analysis-inputs'
import type { Project } from '@/lib/types'

const project: Project = {
  id: 'p1', name: 'Website', industry: 'Development', scope: 'Build five pages',
  startDate: '2026-10-01', pricingModel: 'hourly', currency: 'USD', hourlyRate: '100.00', fixedPrice: null,
  history: [],
}

const input = {
  industry: 'Development' as const, scope: 'Build five pages',
  startDate: '2026-10-01', pricingModel: 'hourly' as const, currency: 'USD' as const,
  hourlyRate: '100.00', fixedPrice: '',
}

describe('project analysis inputs', () => {
  it.each([
    ['industry', 'Design'],
    ['scope', 'Build six pages'],
    ['startDate', '2026-10-02'],
    ['pricingModel', 'fixed'],
    ['currency', 'EUR'],
    ['hourlyRate', '120'],
    ['fixedPrice', '10000'],
  ] as const)('detects a changed %s', (field, value) => {
    expect(projectAnalysisInputsChanged(project, { ...input, [field]: value })).toBe(true)
  })

  it('does not invalidate analysis for a name-only edit', () => {
    expect(projectAnalysisInputsChanged({ ...project, name: 'Renamed website' }, input)).toBe(false)
  })
})
