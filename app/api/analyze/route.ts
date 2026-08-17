import { NextResponse } from 'next/server'
import { ERROR_CODES } from '@/lib/api/errors'
import { jsonError, readJsonObject } from '@/lib/api/json'
import { getCurrentUser } from '@/lib/auth/current-user'
import { parseAnalyzeBody } from '@/lib/llm/analyze-request'
import { analyzeWithOpenAI } from '@/lib/llm/openai'
import { loadProjectForUser } from '@/lib/projects/data'

export async function POST(request: Request) {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)

  const body = await readJsonObject(request)
  if (!body) return jsonError(ERROR_CODES.requestBodyInvalid, 400)

  const parsed = parseAnalyzeBody(body)
  if (!parsed.ok) return jsonError(parsed.error, 400)

  const project = await loadProjectForUser(parsed.projectId, user.id)
  if (!project) return jsonError(ERROR_CODES.projectNotFound, 404)

  if (project.scope.trim().length === 0) {
    return jsonError(ERROR_CODES.scopeRequired, 400)
  }

  try {
    const result = await analyzeWithOpenAI({
      scope: project.scope,
      request: parsed.request,
      industry: project.industry,
    })
    return NextResponse.json({ result })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'unknown'
    console.error(
      JSON.stringify({
        event: 'analyze_route_failed',
        userId: user.id,
        projectId: project.id,
        message,
      }),
    )
    if (message === 'openai_api_key_missing') {
      return jsonError(ERROR_CODES.analysisUnavailable, 503)
    }
    return jsonError(ERROR_CODES.analysisFailed, 502)
  }
}
