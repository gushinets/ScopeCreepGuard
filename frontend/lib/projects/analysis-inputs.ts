import type { Project } from '@/lib/types'

type ProjectAnalysisInput = Pick<Project, 'industry' | 'scope' | 'startDate' | 'pricingModel' | 'currency'> & {
  hourlyRate: string | null
  fixedPrice: string | null
}
const money = (value: string | null) => value == null || value === '' ? null : Number(value)

export function projectAnalysisInputsChanged(project: Project, input: ProjectAnalysisInput): boolean {
  return project.industry !== input.industry ||
    project.scope !== input.scope ||
    project.startDate !== input.startDate ||
    project.pricingModel !== input.pricingModel ||
    project.currency !== input.currency ||
    money(project.hourlyRate) !== money(input.hourlyRate) ||
    money(project.fixedPrice) !== money(input.fixedPrice)
}
