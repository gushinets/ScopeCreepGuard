import { NextResponse } from 'next/server'
import { and, eq } from 'drizzle-orm'
import { ERROR_CODES } from '@/lib/api/errors'
import { jsonError, readJsonObject } from '@/lib/api/json'
import { getCurrentUser } from '@/lib/auth/current-user'
import { loadProjectForUser } from '@/lib/projects/data'
import { parseProjectInput } from '@/lib/projects/validation'
import { db } from '@/lib/db'
import { projects } from '@/lib/db/schema'

interface ProjectRouteContext {
  params: Promise<{ id: string }>
}

export async function GET(_request: Request, { params }: ProjectRouteContext) {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)

  const { id } = await params
  const project = await loadProjectForUser(id, user.id)
  if (!project) return jsonError(ERROR_CODES.projectNotFound, 404)

  return NextResponse.json({ project })
}

export async function PATCH(request: Request, { params }: ProjectRouteContext) {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)
  const { id } = await params
  const current = await loadProjectForUser(id, user.id)
  if (!current) return jsonError(ERROR_CODES.projectNotFound, 404)
  const body = await readJsonObject(request)
  if (!body) return jsonError(ERROR_CODES.requestBodyInvalid, 400)
  const parsed = parseProjectInput(body)
  if (!parsed.ok) return jsonError(parsed.error, 400)
  const [row] = await db.update(projects).set(parsed.project).where(and(eq(projects.id, id), eq(projects.userId, user.id))).returning()
  if (!row) return jsonError(ERROR_CODES.projectNotFound, 404)
  return NextResponse.json({ project: { ...current, ...parsed.project } })
}
