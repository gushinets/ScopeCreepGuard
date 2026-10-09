import { and, desc, eq, sql } from 'drizzle-orm'
import { db } from '@/lib/db'
import { drafts, historyEntries, projects } from '@/lib/db/schema'
import type { HistoryEntry } from '@/lib/types'
import type { Locale } from '@/i18n/config'
import type { CreateDraftInput, DraftDocument, DraftListItem, SavedDraft } from './types'

function serialize(row: typeof drafts.$inferSelect, request: string): SavedDraft {
  return {
    id: row.id, projectId: row.projectId, historyEntryId: row.historyEntryId, request,
    createdAt: row.createdAt.toISOString(), updatedAt: row.updatedAt.toISOString(),
    status: 'draft', locale: row.locale as Locale,
    requestLanguage: row.requestLanguage as SavedDraft['requestLanguage'],
    clientMaterialLanguage: row.clientMaterialLanguage,
    projectSnapshot: row.projectSnapshot, analysisSnapshot: row.analysisSnapshot, draftDocument: row.draftDocument,
  }
}
function languageData(document: DraftDocument) {
  const material = document.clientMaterials
  return {
    clientMaterialLanguage: material?.clientLanguage ?? document.result.clientLanguage ?? document.changeOrder?.language ?? 'en',
    changeOrderLabels: document.changeOrder?.changeOrderLabels ?? material?.changeOrderLabels ?? document.result.changeOrderLabels ?? null,
  }
}
export async function createDraftForUser(userId: string, input: CreateDraftInput) {
  return db.transaction(async (tx) => {
    // Serialize creation for this project before checking the unique retry token.
    const [project] = await tx.select({ id: projects.id }).from(projects)
      .where(and(eq(projects.id, input.projectId), eq(projects.userId, userId))).for('update')
    if (!project) return null
    const [existing] = await tx.select({ draft: drafts, entry: historyEntries }).from(drafts)
      .innerJoin(historyEntries, eq(historyEntries.id, drafts.historyEntryId))
      .where(and(eq(drafts.projectId, input.projectId), eq(drafts.idempotencyKey, input.idempotencyKey)))
    if (existing) return {
      draft: serialize(existing.draft, existing.entry.request),
      entry: { ...existing.entry, draftId: existing.draft.id } as HistoryEntry,
      created: false,
    }
    const now = new Date()
    const date = now.toISOString().slice(0, 10)
    const [entry] = await tx.insert(historyEntries).values({
      projectId: input.projectId, date, request: input.request,
      verdict: input.analysisSnapshot.verdict, summary: input.analysisSnapshot.summary,
    }).returning()
    if (!entry) throw new Error('history_insert_missing')
    const [draft] = await tx.insert(drafts).values({
      projectId: input.projectId, historyEntryId: entry.id, idempotencyKey: input.idempotencyKey,
      projectSnapshot: input.projectSnapshot, analysisSnapshot: input.analysisSnapshot, draftDocument: input.draftDocument, locale: input.locale,
      requestLanguage: input.analysisSnapshot.requestLanguage ?? null,
      ...languageData(input.draftDocument), createdAt: now, updatedAt: now,
    }).returning()
    if (!draft) throw new Error('draft_insert_missing')
    await tx.update(projects).set({ lastChecked: date }).where(eq(projects.id, input.projectId))
    return { draft: serialize(draft, entry.request), entry: { ...entry, draftId: draft.id } as HistoryEntry, created: true }
  })
}
export async function loadDraftForUser(id: string, userId: string): Promise<SavedDraft | null> {
  const [row] = await db.select({ draft: drafts, request: historyEntries.request }).from(drafts)
    .innerJoin(projects, eq(projects.id, drafts.projectId))
    .innerJoin(historyEntries, eq(historyEntries.id, drafts.historyEntryId))
    .where(and(eq(drafts.id, id), eq(projects.userId, userId))).limit(1)
  return row ? serialize(row.draft, row.request) : null
}
export async function listDraftsForUser(userId: string): Promise<DraftListItem[]> {
  const rows = await db.select({
    id: drafts.id, request: historyEntries.request, projectName: sql<string>`coalesce(${drafts.projectSnapshot}->>'name', ${drafts.draftDocument}->'changeOrder'->>'projectName', ${projects.name})`,
    verdict: historyEntries.verdict, createdAt: drafts.createdAt, updatedAt: drafts.updatedAt,
  }).from(drafts)
    .innerJoin(projects, eq(projects.id, drafts.projectId))
    .innerJoin(historyEntries, eq(historyEntries.id, drafts.historyEntryId))
    .where(eq(projects.userId, userId)).orderBy(desc(drafts.createdAt), desc(drafts.id))
  return rows.map(({ request, createdAt, updatedAt, ...row }) => ({
    ...row, requestPreview: request.length > 160 ? request.slice(0, 157) + '…' : request,
    createdAt: createdAt.toISOString(), updatedAt: updatedAt.toISOString(),
  }))
}
export async function updateDraftForUser(id: string, userId: string, document: DraftDocument) {
  // Ownership remains part of the update predicate, not just the preceding read.
  const ownedProjects = db.select({ id: projects.id }).from(projects).where(eq(projects.userId, userId))
  const { inArray } = await import('drizzle-orm')
  const [row] = await db.update(drafts).set({
    draftDocument: document, ...languageData(document), updatedAt: new Date(),
  }).where(and(eq(drafts.id, id), inArray(drafts.projectId, ownedProjects))).returning()
  if (!row) return null
  return loadDraftForUser(id, userId)
}
