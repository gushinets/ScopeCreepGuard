import type { Currency } from './models'
import type { ChangeOrderLabels as ClientLabels } from './labels'
export interface EditableDraft {
  aiValues?: Partial<Record<'description' | 'estimatedHours' | 'additionalCost' | 'currency' | 'timelineImpact' | 'rationale' | 'note' | 'manualPrice' | 'manualEffort' | 'manualRationale', string>>
  reference?: string
  createdAt: string
  language: string
  changeOrderLabels?: ClientLabels
  projectName: string
  description: string
  estimatedHours: string
  additionalCost: string
  currency: Currency | ''
  timelineImpact: string
  rationale: string
  note: string
  providerName: string
  clientName: string
  clientEmail: string
  endDate: string
  additionalTerms: string
  clientApproverName: string
  approvalDate: string
  noAdditionalCharge: boolean
}
