
import type { Project } from '@/lib/types'
import type { ProjectSnapshot } from './types'

export function snapshotProject(project: Project, endDate?: string, documentLanguage?: string): ProjectSnapshot {
  return {
    version: 1, name: project.name, industry: project.industry, scope: project.scope,
    startDate: project.startDate, endDate: endDate ?? null, pricingModel: project.pricingModel,
    currency: project.currency, hourlyRate: project.hourlyRate, fixedPrice: project.fixedPrice,
    documentLanguage: documentLanguage ?? null,
  }
}
