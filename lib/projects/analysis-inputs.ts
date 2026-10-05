import type { Currency, Industry, PricingModel, Project } from '@/lib/types'

export interface ProjectAnalysisInput {
  industry: Industry
  scope: string
  startDate: string
  pricingModel: PricingModel
  currency: Currency
  hourlyRate: string
  fixedPrice: string
}

export function projectAnalysisInputsChanged(project: Project, input: ProjectAnalysisInput): boolean {
  return project.industry !== input.industry ||
    project.scope !== input.scope ||
    project.startDate !== input.startDate ||
    project.pricingModel !== input.pricingModel ||
    project.currency !== input.currency ||
    (project.hourlyRate ?? '') !== input.hourlyRate ||
    (project.fixedPrice ?? '') !== input.fixedPrice
}
