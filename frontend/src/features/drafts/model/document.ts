import type { AnalysisResult, Project } from '@/shared/api/models'
import type { ProjectDetails } from '@/features/projects/contracts'
import type { EditableDraft } from '@/shared/api/documents'
import { makeChangeOrderReference } from '@/features/change-orders/contracts'

export function editableChangeOrder(result: AnalysisResult, project: Project, details: ProjectDetails, seed: string): EditableDraft {
  const co = result.changeOrder
  if (!co) throw new Error('Agreement has not been prepared')
  const createdAt = result.draftCreatedAt ?? new Date().toISOString()
  return {
    reference: makeChangeOrderReference(createdAt, seed), createdAt,
    language: result.clientLanguage ?? (result.requestLanguage && result.requestLanguage !== 'other' ? result.requestLanguage : 'en'),
    ...(result.changeOrderLabels ? { changeOrderLabels: result.changeOrderLabels } : {}),
    projectName: project.name, description: co.description,
    estimatedHours: co.estimatedHours?.toString() ?? '', additionalCost: co.additionalCost,
    currency: co.currency ?? '', timelineImpact: co.timelineImpact, rationale: co.rationale ?? '', note: co.note,
    providerName: '', ...details, clientName: project.clientName === undefined ? details.clientName : project.clientName ?? '', additionalTerms: '', clientApproverName: '', approvalDate: '', noAdditionalCharge: false,
    aiValues: { description: co.description, estimatedHours: co.estimatedHours?.toString() ?? '', additionalCost: co.additionalCost, currency: co.currency ?? '', timelineImpact: co.timelineImpact, rationale: co.rationale ?? '', note: co.note },
  }
}
