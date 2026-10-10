import { and, desc, eq } from 'drizzle-orm'
import { db } from '@/lib/db'
import { drafts, historyEntries, projects } from '@/lib/db/schema'
import type { HistoryEntry, Project } from '@/lib/types'

function serializeHistoryEntry(row: typeof historyEntries.$inferSelect & { draftId?: string | null }): HistoryEntry {
  return {
    id: row.id,
    ...(row.draftId ? { draftId: row.draftId } : {}),
    date: row.date,
    request: row.request,
    verdict: row.verdict,
    summary: row.summary,
  }
}

export function serializeProject(
  row: typeof projects.$inferSelect,
  history: HistoryEntry[],
): Project {
  return {
    id: row.id,
    name: row.name,
    clientName: row.client,
    industry: row.industry,
    scope: row.scope,
    startDate: row.startDate,
    pricingModel: row.pricingModel,
    currency: row.currency,
    hourlyRate: row.hourlyRate,
    fixedPrice: row.fixedPrice,
    lastChecked: row.lastChecked ?? undefined,
    history,
  }
}

export async function loadProjectForUser(projectId: string, userId: string) {
  const [project] = await db
    .select()
    .from(projects)
    .where(and(eq(projects.id, projectId), eq(projects.userId, userId)))
    .limit(1)

  if (!project) return null

  const history = await db
    .select({ id: historyEntries.id, projectId: historyEntries.projectId, date: historyEntries.date, request: historyEntries.request, verdict: historyEntries.verdict, summary: historyEntries.summary, draftId: drafts.id })
    .from(historyEntries)
    .leftJoin(drafts, eq(drafts.historyEntryId, historyEntries.id))
    .where(eq(historyEntries.projectId, project.id))
    .orderBy(desc(historyEntries.date))

  return serializeProject(project, history.map(serializeHistoryEntry))
}

export async function userOwnsProject(projectId: string, userId: string) {
  const [project] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, projectId), eq(projects.userId, userId)))
    .limit(1)

  return Boolean(project)
}
