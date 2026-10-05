import type { Project } from '@/lib/types'

export function commercialSignature(project: Pick<Project, 'pricingModel' | 'currency' | 'hourlyRate' | 'fixedPrice' | 'startDate'>, endDate?: string) {
  return JSON.stringify([project.pricingModel, project.currency, project.hourlyRate, project.fixedPrice, project.startDate, endDate ?? ''])
}
