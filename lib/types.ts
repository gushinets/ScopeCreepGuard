export type Industry = 'Development' | 'Design' | 'Marketing'

export type Verdict = 'in_scope' | 'borderline' | 'out_of_scope'

export type EvaluationAccuracy = 'correct' | 'wrong' | 'debatable'

export type Tone = 'warm' | 'neutral' | 'firm'

export type PricingModel = 'hourly' | 'fixed'
export type Currency = 'RUB' | 'USD' | 'EUR'

export interface ChangeOrderDraft {
  description: string
  timelineImpact: string
  additionalCost: string
  note: string
  estimatedHours?: number
  currency?: Currency | ''
  rationale?: string
}

export interface AnalysisResult {
  verdict: Verdict
  /** Integer 0-100, percent certainty. */
  confidence: number
  summary: string
  reasoning: string
  citations: string[]
  suggestion?: string
  replies: Record<Tone, string>
  changeOrder: ChangeOrderDraft
  hasAdditionalWork?: boolean
  requestLanguage?: 'ru' | 'en' | 'es' | 'other'
  clientLanguage?: string
  changeOrderLabels?: import('./change-order/labels').ChangeOrderLabels
  draftCreatedAt?: string
  commercialSignature?: string
  estimateValid?: boolean
}

export interface HistoryEntry {
  id: string
  date: string
  request: string
  verdict: Verdict
  summary: string
}

export interface Project {
  id: string
  name: string
  industry: Industry
  scope: string
  startDate: string | null
  pricingModel: PricingModel | null
  currency: Currency | null
  hourlyRate: string | null
  fixedPrice: string | null
  lastChecked?: string
  history: HistoryEntry[]
}
