import { NextResponse } from 'next/server'
import { ERROR_CODES } from '@/lib/api/errors'
import { jsonError } from '@/lib/api/json'
import { getCurrentUser } from '@/lib/auth/current-user'
import { loadProjectForUser } from '@/lib/projects/data'

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
