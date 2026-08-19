import { and, asc, eq } from 'drizzle-orm'
import { db } from '@/lib/db'
import { evaluationCases, historyEntries, projects } from '@/lib/db/schema'
import type { EvaluationAccuracy, Industry, Verdict } from '@/lib/types'

export interface EvaluationUpsertInput {
  userId: string
  historyEntryId: string
  scope: string
  request: string
  aiVerdict: Verdict
  humanVerdict: Verdict | null
  aiReasoning: string
  accuracy: EvaluationAccuracy
  industry: Industry
}

export async function loadHistoryForUser(historyEntryId: string, userId: string) {
  const [row] = await db
    .select({
      history: historyEntries,
      project: projects,
    })
    .from(historyEntries)
    .innerJoin(projects, eq(historyEntries.projectId, projects.id))
    .where(and(eq(historyEntries.id, historyEntryId), eq(projects.userId, userId)))
    .limit(1)

  if (!row) return null
  return row
}

export async function upsertEvaluationCase(input: EvaluationUpsertInput) {
  const [row] = await db
    .insert(evaluationCases)
    .values({
      userId: input.userId,
      historyEntryId: input.historyEntryId,
      scope: input.scope,
      request: input.request,
      aiVerdict: input.aiVerdict,
      humanVerdict: input.humanVerdict,
      aiReasoning: input.aiReasoning,
      accuracy: input.accuracy,
      industry: input.industry,
    })
    .onConflictDoUpdate({
      target: evaluationCases.historyEntryId,
      set: {
        userId: input.userId,
        scope: input.scope,
        request: input.request,
        aiVerdict: input.aiVerdict,
        humanVerdict: input.humanVerdict,
        aiReasoning: input.aiReasoning,
        accuracy: input.accuracy,
        industry: input.industry,
        updatedAt: new Date(),
      },
    })
    .returning()

  if (!row) {
    console.error(
      JSON.stringify({
        event: 'evaluation_upsert_failed',
        userId: input.userId,
      }),
    )
    throw new Error('Evaluation case was not saved.')
  }

  return {
    id: row.id,
    accuracy: row.accuracy,
    humanVerdict: row.humanVerdict,
  }
}

export async function listEvaluationCasesForUser(userId: string) {
  return db
    .select({
      scope: evaluationCases.scope,
      request: evaluationCases.request,
      aiVerdict: evaluationCases.aiVerdict,
      humanVerdict: evaluationCases.humanVerdict,
      aiReasoning: evaluationCases.aiReasoning,
      industry: evaluationCases.industry,
    })
    .from(evaluationCases)
    .where(eq(evaluationCases.userId, userId))
    .orderBy(asc(evaluationCases.createdAt), asc(evaluationCases.id))
}
