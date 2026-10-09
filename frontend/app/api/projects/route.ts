import { NextResponse, type NextRequest } from 'next/server'
import { ERROR_CODES } from '@/lib/api/errors'
import { jsonError, readJsonObject } from '@/lib/api/json'
import { getCurrentUser } from '@/lib/auth/current-user'
import { db } from '@/lib/db'
import { projects } from '@/lib/db/schema'
import { loadProjectsForUser } from '@/lib/projects/data'
import { parseProjectInput } from '@/lib/projects/validation'
import type { Project } from '@/lib/types'

function serializeCreatedProject(row: typeof projects.$inferSelect): Project {
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
    history: [],
  }
}

export async function GET() {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)

  const userProjects = await loadProjectsForUser(user.id)
  return NextResponse.json({ projects: userProjects })
}

export async function POST(request: NextRequest) {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)

  const body = await readJsonObject(request)
  if (!body) return jsonError(ERROR_CODES.requestBodyInvalid, 400)

  const parsed = parseProjectInput(body)
  if (!parsed.ok) return jsonError(parsed.error, 400)

  const [project] = await db
    .insert(projects)
    .values({
      userId: user.id,
      name: parsed.project.name,
      client: parsed.project.client ?? null,
      industry: parsed.project.industry,
      scope: parsed.project.scope,
      startDate: parsed.project.startDate,
      pricingModel: parsed.project.pricingModel,
      currency: parsed.project.currency,
      hourlyRate: parsed.project.hourlyRate,
      fixedPrice: parsed.project.fixedPrice,
    })
    .returning()

  if (!project) {
    console.error(JSON.stringify({ event: 'project_insert_missing', userId: user.id }))
    throw new Error('Project was not created.')
  }

  return NextResponse.json({ project: serializeCreatedProject(project) }, { status: 201 })
}
