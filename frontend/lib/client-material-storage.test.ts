// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from 'vitest'
import type { AnalysisResult, Project } from './types'
import { applyClientMaterials, parseClientMaterials } from './client-materials'
import { readActiveClientResult, readClientResult, saveClientResult, updateSavedClientDraft } from './client-material-storage'
import { germanLabels } from './change-order/german-fixture'
import { normalizeChangeOrderDraft, readChangeOrder, writeChangeOrder } from './change-order/draft-storage'

const analysis: AnalysisResult = { verdict: 'out_of_scope', confidence: 85, summary: 'Extra page', reasoning: 'Not included', citations: ['Five pages'], suggestion: 'Get approval', replies: { warm: 'Hello', neutral: 'Extra page', firm: 'Approve' }, clientLanguage: 'en', hasAdditionalWork: true, changeOrder: { description: 'Extra page', timelineImpact: 'Two days', additionalCost: '200', estimatedHours: 2, currency: 'EUR', rationale: 'Extra', note: 'Draft' }, draftCreatedAt: '2026-10-06', estimateValid: true, commercialSignature: 'terms' }
const project: Project = { id: 'p1', name: 'Site', industry: 'Development', scope: 'Five pages', startDate: '2026-01-01', pricingModel: 'hourly', currency: 'EUR', hourlyRate: '100', fixedPrice: null, history: [{ id: 'h1', date: '2026-10-06', request: 'Add a page', verdict: analysis.verdict, summary: analysis.summary }] }
const materials = parseClientMaterials({ clientLanguage: 'de', replies: { warm: 'Danke', neutral: 'Neue Seite', firm: 'Bitte genehmigen' }, changeOrder: { description: 'Neue Seite', timelineImpact: 'Zwei Tage', rationale: 'Zusätzliche Leistung', note: 'Entwurf' }, changeOrderLabels: germanLabels })
beforeEach(() => localStorage.clear())

describe('client material persistence', () => {
  it('does not restore an analysis after only the project industry changes', () => {
    saveClientResult('u1', project, 'h1', 'Add a page', 'en', analysis, materials)
    const changed: Project = { ...project, industry: 'Design' }
    expect(readClientResult('u1', changed, 'h1', 'en')).toBeNull()
    expect(readActiveClientResult('u1', [changed], 'en')).toBeNull()
    expect(readActiveClientResult('u1', [project], 'en')).not.toBeNull()
  })

  it('restores materials and established analysis only for the matching user, project, history and context', () => {
    expect(saveClientResult('u1', project, 'h1', 'Add a page', 'en', analysis, materials)).toBe(true)
    expect(readActiveClientResult('u1', [project], 'en')).toMatchObject({ analysis, materials, historyId: 'h1' })
    expect(readActiveClientResult('u2', [project], 'en')).toBeNull()
    expect(readClientResult('u1', project, 'h2', 'en')).toBeNull()
    expect(readActiveClientResult('u1', [{ ...project, scope: 'Changed scope' }], 'en')).toBeNull()
    expect(readActiveClientResult('u1', [{ ...project, currency: 'USD' }], 'en')).toBeNull()
    expect(readActiveClientResult('u1', [project], 'ru')).toBeNull()
  })
  it('cannot replace scope fields or numeric estimates from a material response', () => {
    const raw = { ...materials, verdict: 'in_scope', confidence: 1, hasAdditionalWork: false, changeOrder: { ...materials.changeOrder, additionalCost: '999', estimatedHours: 999, currency: 'USD' } }
    const updated = applyClientMaterials(analysis, parseClientMaterials(raw))
    expect(updated).toMatchObject({ verdict: analysis.verdict, confidence: analysis.confidence, reasoning: analysis.reasoning, citations: analysis.citations, suggestion: analysis.suggestion, hasAdditionalWork: true, changeOrder: { additionalCost: '200', estimatedHours: 2, currency: 'EUR', description: 'Neue Seite' } })
  })
  it('refreshes generated draft text twice while preserving user edits, deletions and monetary fields', () => {
    const draft = normalizeChangeOrderDraft({ createdAt: '2026-10-06', language: 'en', projectName: 'Site', description: 'My custom scope', timelineImpact: 'Two days', additionalCost: '175', estimatedHours: '3', currency: 'EUR', note: '', clientName: 'Anna', aiValues: { description: 'Extra page', timelineImpact: 'Two days', note: 'Draft', additionalCost: '200', estimatedHours: '2', currency: 'EUR' } })!
    writeChangeOrder('u1', 'p1', 'h1', draft)
    updateSavedClientDraft('u1', 'p1', 'h1', materials, 'en')
    expect(readChangeOrder('u1', 'p1', 'h1')).toMatchObject({ language: 'de', description: 'My custom scope', note: '', additionalCost: '175', estimatedHours: '3', timelineImpact: 'Zwei Tage', clientName: 'Anna', changeOrderLabels: germanLabels })
    const next = { ...materials, changeOrder: { ...materials.changeOrder!, description: 'Neue Fassung', timelineImpact: 'Zwei Arbeitstage' } }
    updateSavedClientDraft('u1', 'p1', 'h1', next, 'en')
    expect(readChangeOrder('u1', 'p1', 'h1')).toMatchObject({ description: 'My custom scope', note: '', additionalCost: '175', estimatedHours: '3', timelineImpact: 'Zwei Arbeitstage' })
  })
  it('keeps legacy history and drafts safe when no client-material record exists', () => {
    expect(readActiveClientResult('u1', [project], 'en')).toBeNull()
    localStorage.setItem('scg:client-materials:u1:p1:h1', '{broken')
    expect(readClientResult('u1', project, 'h1', 'en')).toBeNull()
    const draft = normalizeChangeOrderDraft({ createdAt: '2026-10-06', projectName: 'Site', description: 'Legacy edit', approvedBy: 'Anna' }, 'ru')
    expect(draft).toMatchObject({ language: 'ru', description: 'Legacy edit', clientApproverName: 'Anna' })
  })
})
