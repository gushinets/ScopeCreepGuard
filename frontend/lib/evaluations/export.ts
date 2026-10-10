import type { Industry, Verdict } from '@/lib/types'

export type JsonlVerdict = 'IN_SCOPE' | 'BORDERLINE' | 'OUT_OF_SCOPE'
export type JsonlProjectType = 'development' | 'design' | 'marketing'

export interface EvaluationJsonlRecord {
  scope: string
  request: string
  ai_verdict: JsonlVerdict
  human_verdict: JsonlVerdict | null
  ai_reasoning: string
  project_type: JsonlProjectType
}

const VERDICT_JSONL: Record<Verdict, JsonlVerdict> = {
  in_scope: 'IN_SCOPE',
  borderline: 'BORDERLINE',
  out_of_scope: 'OUT_OF_SCOPE',
}

const INDUSTRY_JSONL: Record<Industry, JsonlProjectType> = {
  Development: 'development',
  Design: 'design',
  Marketing: 'marketing',
}

export function toEvaluationJsonlRecord(row: {
  scope: string
  request: string
  aiVerdict: Verdict
  humanVerdict: Verdict | null
  aiReasoning: string
  industry: Industry
}): EvaluationJsonlRecord {
  const human_verdict =
    row.humanVerdict === null ? null : VERDICT_JSONL[row.humanVerdict]
  return {
    scope: row.scope,
    request: row.request,
    ai_verdict: VERDICT_JSONL[row.aiVerdict],
    human_verdict,
    ai_reasoning: row.aiReasoning,
    project_type: INDUSTRY_JSONL[row.industry],
  }
}

export function serializeEvaluationJsonl(records: EvaluationJsonlRecord[]): string {
  if (records.length === 0) return ''
  return `${records.map((record) => JSON.stringify(record)).join('\n')}\n`
}
