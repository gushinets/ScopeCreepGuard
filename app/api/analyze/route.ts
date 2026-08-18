import { NextResponse } from 'next/server'
import { getLocale } from 'next-intl/server'
import { isLocale } from '@/i18n/config'
import { ERROR_CODES } from '@/lib/api/errors'
import { jsonError, readJsonObject } from '@/lib/api/json'
import { getCurrentUser } from '@/lib/auth/current-user'
import { parseAnalyzeBody } from '@/lib/llm/analyze-request'
import { analyzeWithOpenAI } from '@/lib/llm/openai'
import { allowAnalyze } from '@/lib/llm/rate-limit'
import { loadProjectForUser } from '@/lib/projects/data'

const ANALYSIS_INPUT_MAX_CHARS = 100_000

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

  if (!allowAnalyze(user.id, Date.now())) {
    console.error(
      JSON.stringify({
        event: 'analyze_rate_limited',
        userId: user.id,
      }),
    )
    return jsonError(ERROR_CODES.analysisRateLimited, 429)
  }

  if (project.scope.length + parsed.request.length > ANALYSIS_INPUT_MAX_CHARS) {
    return jsonError(ERROR_CODES.analysisInputTooLarge, 400)
  }

  const locale = await getLocale()
  if (!isLocale(locale)) {
    console.error(
      JSON.stringify({
        event: 'analyze_locale_invalid',
        userId: user.id,
        locale,
      }),
    )
    throw new Error(`Invalid locale: ${locale}`)
  }

  try {
    const result = await analyzeWithOpenAI({
      scope: project.scope,
      request: parsed.request,
      industry: project.industry,
      locale,
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
