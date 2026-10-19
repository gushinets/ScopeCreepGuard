
import type { Project } from '@/shared/api/models'
import type { ProjectSnapshot } from '@/features/drafts/model/types'

export function snapshotProject(project: Project, endDate?: string, documentLanguage?: string): ProjectSnapshot {
  return {
    ...(project.clientName !== undefined ? { clientName: project.clientName } : {}),
    version: 1, name: project.name, industry: project.industry, scope: project.scope,
    startDate: project.startDate, endDate: endDate ?? null, pricingModel: project.pricingModel,
    currency: project.currency, hourlyRate: project.hourlyRate, fixedPrice: project.fixedPrice,
    documentLanguage: documentLanguage ?? null,
  }
}
