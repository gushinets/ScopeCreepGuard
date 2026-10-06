import { NextResponse } from 'next/server'
import { getLocale } from 'next-intl/server'
import { isLocale } from '@/i18n/config'
import { ERROR_CODES } from '@/lib/api/errors'
import { jsonError, readJsonObject } from '@/lib/api/json'
import { getCurrentUser } from '@/lib/auth/current-user'
import { loadProjectForUser } from '@/lib/projects/data'
import { supportedClientLanguage } from '@/lib/client-language'
import { parseAnalysisResult } from '@/lib/llm/schema'
import { regenerateClientMaterials } from '@/lib/llm/client-materials'
import { ANALYSIS_INPUT_MAX_CHARS } from '@/lib/llm/analyze-request'
import { analyzeFailureResponse } from '@/lib/llm/openai'
import { allowAnalyze } from '@/lib/llm/rate-limit'

export async function POST(request: Request) {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)
  const body = await readJsonObject(request)
  if (!body || typeof body.projectId !== 'string' || (body.historyId !== undefined && typeof body.historyId !== 'string') || typeof body.request !== 'string') return jsonError(ERROR_CODES.requestBodyInvalid, 400)
  const clientLanguage = supportedClientLanguage(body.clientLanguage)
  if (!clientLanguage) return jsonError(ERROR_CODES.clientLanguageUnsupported, 400)
  if (JSON.stringify(body).length > ANALYSIS_INPUT_MAX_CHARS) return jsonError(ERROR_CODES.analysisInputTooLarge, 400)
  const project = await loadProjectForUser(body.projectId, user.id)
  if (!project) return jsonError(ERROR_CODES.projectNotFound, 404)
  const history = body.historyId === undefined ? null : project.history.find((entry) => entry.id === body.historyId)
  if (body.historyId !== undefined && (!history || history.request !== body.request)) return jsonError(ERROR_CODES.requestBodyInvalid, 400)
  const locale = await getLocale()
  if (!isLocale(locale)) return jsonError(ERROR_CODES.localeInvalid, 400)
  let analysis
  try { analysis = parseAnalysisResult(body.analysis, locale) }
  catch { return jsonError(ERROR_CODES.requestBodyInvalid, 400) }
  if (history && (analysis.verdict !== history.verdict || analysis.summary !== history.summary)) return jsonError(ERROR_CODES.requestBodyInvalid, 400)
  if (project.scope.length + JSON.stringify(body).length > ANALYSIS_INPUT_MAX_CHARS) return jsonError(ERROR_CODES.analysisInputTooLarge, 400)
  if (!allowAnalyze(user.id, Date.now())) return jsonError(ERROR_CODES.analysisRateLimited, 429)
  try {
    const materials = await regenerateClientMaterials({ locale, clientLanguage, scope: project.scope, request: body.request, analysis })
    return NextResponse.json({ materials })
  } catch (error) {
    const mapped = analyzeFailureResponse(error instanceof Error ? error.message : 'unknown')
    return jsonError(mapped.error, mapped.status)
  }
}
