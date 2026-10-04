import { NextResponse } from 'next/server'
import { getLocale } from 'next-intl/server'
import { isLocale } from '@/i18n/config'
import { ERROR_CODES } from '@/lib/api/errors'
import { jsonError, readJsonObject } from '@/lib/api/json'
import { getCurrentUser } from '@/lib/auth/current-user'
import { ANALYSIS_INPUT_MAX_CHARS } from '@/lib/llm/analyze-request'
import {
  analyzeFailureResponse,
  regenerateReplyWithOpenAI,
} from '@/lib/llm/openai'
import { allowAnalyze } from '@/lib/llm/rate-limit'
import { parseRegenerateReplyBody } from '@/lib/llm/regenerate-request'
import { loadProjectForUser } from '@/lib/projects/data'

export async function POST(request: Request) {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)

  const body = await readJsonObject(request)
  if (!body) return jsonError(ERROR_CODES.requestBodyInvalid, 400)

  const parsed = parseRegenerateReplyBody(body)
  if (!parsed.ok) return jsonError(parsed.error, 400)

  const project = await loadProjectForUser(parsed.value.projectId, user.id)
  if (!project) return jsonError(ERROR_CODES.projectNotFound, 404)

  if (project.scope.trim().length === 0) {
    return jsonError(ERROR_CODES.scopeRequired, 400)
  }

  if (
    project.scope.length +
      parsed.value.request.length +
      parsed.value.previousReply.length >
    ANALYSIS_INPUT_MAX_CHARS
  ) {
    return jsonError(ERROR_CODES.analysisInputTooLarge, 400)
  }

  if (!allowAnalyze(user.id, Date.now())) {
    console.error(
      JSON.stringify({
        event: 'reply_regeneration_rate_limited',
        userId: user.id,
      }),
    )
    return jsonError(ERROR_CODES.analysisRateLimited, 429)
  }

  const locale = await getLocale()
  if (!isLocale(locale)) {
    console.error(
      JSON.stringify({
        event: 'reply_regeneration_locale_invalid',
        userId: user.id,
        locale,
      }),
    )
    return jsonError(ERROR_CODES.localeInvalid, 400)
  }

  try {
    const reply = await regenerateReplyWithOpenAI({
      scope: project.scope,
      request: parsed.value.request,
      industry: project.industry,
      locale,
      tone: parsed.value.tone,
      previousReply: parsed.value.previousReply,
    })
    return NextResponse.json({ reply })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'unknown'
    console.error(
      JSON.stringify({
        event: 'reply_regeneration_route_failed',
        userId: user.id,
        projectId: project.id,
        message,
      }),
    )
    const mapped = analyzeFailureResponse(message)
    return jsonError(mapped.error, mapped.status)
  }
}
