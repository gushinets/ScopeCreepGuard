import { NextResponse, type NextRequest } from 'next/server'
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
    client: row.client ?? undefined,
    industry: row.industry,
    scope: row.scope,
    lastChecked: row.lastChecked ?? undefined,
    history: [],
  }
}

export async function GET() {
  const user = await getCurrentUser()
  if (!user) return jsonError('Authentication is required.', 401)

  const userProjects = await loadProjectsForUser(user.id)
  return NextResponse.json({ projects: userProjects })
}

export async function POST(request: NextRequest) {
  const user = await getCurrentUser()
  if (!user) return jsonError('Authentication is required.', 401)

  const body = await readJsonObject(request)
  if (!body) return jsonError('Request body must be a JSON object.', 400)

  const parsed = parseProjectInput(body)
  if (!parsed.ok) return jsonError(parsed.error, 400)

  const [project] = await db
    .insert(projects)
    .values({
      userId: user.id,
      name: parsed.project.name,
      client: parsed.project.client,
      industry: parsed.project.industry,
      scope: parsed.project.scope,
    })
    .returning()

  if (!project) {
    console.error(JSON.stringify({ event: 'project_insert_missing', userId: user.id }))
    throw new Error('Project was not created.')
  }

  return NextResponse.json({ project: serializeCreatedProject(project) }, { status: 201 })
}
