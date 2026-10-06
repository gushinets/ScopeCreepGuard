import type { AnalysisResult, Project } from '@/lib/types'
import type { ProjectDetails } from '@/lib/projects/browser-details'
import type { EditableDraft } from '@/lib/change-order/document'
import { makeChangeOrderReference } from '@/lib/change-order/document'

export function editableChangeOrder(result: AnalysisResult, project: Project, details: ProjectDetails, seed: string): EditableDraft {
  const co = result.changeOrder
  const createdAt = result.draftCreatedAt ?? new Date().toISOString()
  return {
    reference: makeChangeOrderReference(createdAt, seed), createdAt,
    language: result.clientLanguage ?? (result.requestLanguage && result.requestLanguage !== 'other' ? result.requestLanguage : 'en'),
    ...(result.changeOrderLabels ? { changeOrderLabels: result.changeOrderLabels } : {}),
    projectName: project.name, description: co.description,
    estimatedHours: co.estimatedHours?.toString() ?? '', additionalCost: co.additionalCost,
    currency: co.currency ?? '', timelineImpact: co.timelineImpact, rationale: co.rationale ?? '', note: co.note,
    providerName: '', ...details, additionalTerms: '', clientApproverName: '', approvalDate: '', noAdditionalCharge: false,
    aiValues: { description: co.description, estimatedHours: co.estimatedHours?.toString() ?? '', additionalCost: co.additionalCost, currency: co.currency ?? '', timelineImpact: co.timelineImpact, rationale: co.rationale ?? '', note: co.note },
  }
}
