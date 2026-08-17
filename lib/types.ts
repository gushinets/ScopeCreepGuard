export type Industry = 'Development' | 'Design' | 'Marketing'

export type Verdict = 'in_scope' | 'borderline' | 'out_of_scope'

export type Tone = 'warm' | 'neutral' | 'firm'

export interface ChangeOrderDraft {
  description: string
  timelineImpact: string
  additionalCost: string
  note: string
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
  client?: string
  industry: Industry
  scope: string
  lastChecked?: string
  history: HistoryEntry[]
}
