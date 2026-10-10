import { and, eq } from 'drizzle-orm'
import { NextResponse, type NextRequest } from 'next/server'
import { ERROR_CODES } from '@/lib/api/errors'
import { jsonError, readJsonObject } from '@/lib/api/json'
import { getCurrentUser } from '@/lib/auth/current-user'
import { db } from '@/lib/db'
import { historyEntries, projects } from '@/lib/db/schema'
import { userOwnsProject } from '@/lib/projects/data'
import { parseHistoryInput } from '@/lib/projects/validation'

interface HistoryRouteContext {
  params: Promise<{ id: string }>
}

export async function POST(request: NextRequest, { params }: HistoryRouteContext) {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)

  const { id } = await params
  const isOwner = await userOwnsProject(id, user.id)
  if (!isOwner) return jsonError(ERROR_CODES.projectNotFound, 404)

  const body = await readJsonObject(request)
  if (!body) return jsonError(ERROR_CODES.requestBodyInvalid, 400)

  const parsed = parseHistoryInput(body)
  if (!parsed.ok) return jsonError(parsed.error, 400)

  const entry = await db.transaction(async (tx) => {
    const [createdEntry] = await tx
      .insert(historyEntries)
      .values({
        projectId: id,
        date: parsed.entry.date,
        request: parsed.entry.request,
        verdict: parsed.entry.verdict,
        summary: parsed.entry.summary,
      })
      .returning()

    if (!createdEntry) {
      console.error(
        JSON.stringify({
          event: 'history_insert_missing',
          userId: user.id,
          projectId: id,
        }),
      )
      throw new Error('History entry was not created.')
    }

    await tx
      .update(projects)
      .set({ lastChecked: parsed.entry.date })
      .where(and(eq(projects.id, id), eq(projects.userId, user.id)))

    return {
      id: createdEntry.id,
      date: createdEntry.date,
      request: createdEntry.request,
      verdict: createdEntry.verdict,
      summary: createdEntry.summary,
    }
  })

  return NextResponse.json({ entry }, { status: 201 })
}
