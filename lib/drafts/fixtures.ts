import type { AnalysisResult } from '@/lib/types'
import type { DraftDocument } from './types'

export const analysisFixture: AnalysisResult = {
  verdict: 'out_of_scope', confidence: 90, summary: 'Extra page', reasoning: 'Not included',
  citations: ['Five pages'], suggestion: 'Get approval', requestLanguage: 'en', clientLanguage: 'en',
  replies: { warm: 'Hello', neutral: 'Extra work', firm: 'Approve first' },
  changeOrder: { description: 'Extra page', timelineImpact: 'Two days', additionalCost: '200', estimatedHours: 2, currency: 'EUR', rationale: 'Extra work', note: 'Draft' },
  hasAdditionalWork: true, estimateValid: true, draftCreatedAt: '2026-10-06T12:00:00.000Z', commercialSignature: 'original-terms',
}
export const documentFixture: DraftDocument = {
  version: 1, result: analysisFixture, clientMaterials: null,
  reply: { tone: 'firm', text: 'My edited reply', generated: { ...analysisFixture.replies } },
  projectDetails: { clientName: 'Client', clientEmail: 'client@example.test', endDate: '2026-12-01' },
  changeOrder: {
    reference: 'CO-20261006-DRAFT1', createdAt: '2026-10-06T12:00:00.000Z', language: 'en', projectName: 'Website',
    description: 'My own scope', estimatedHours: '1.5', additionalCost: '175', currency: 'EUR',
    timelineImpact: 'Three days', rationale: 'Adjusted estimate', note: 'My note', providerName: 'North Studio',
    clientName: 'Client', clientEmail: 'client@example.test', endDate: '2026-12-01', additionalTerms: 'Pay upfront',
    clientApproverName: 'Ana', approvalDate: '2026-10-07', noAdditionalCharge: false,
    aiValues: { description: 'Extra page', additionalCost: '200' },
  },
}


export const projectSnapshotFixture: import('./types').ProjectSnapshot = {
  version: 1, name: 'Website', industry: 'Development',
  scope: 'Build exactly five pages. Further pages are outside the agreed scope.',
  startDate: '2026-01-01', endDate: null, pricingModel: 'hourly', currency: 'EUR',
  hourlyRate: '100.00', fixedPrice: null, documentLanguage: null,
}
