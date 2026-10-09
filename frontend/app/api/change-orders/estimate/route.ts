import { generationProject } from '@/lib/drafts/generation-context'
import { NextResponse } from 'next/server'
import { getLocale } from 'next-intl/server'
import { isLocale } from '@/i18n/config'
import { ERROR_CODES } from '@/lib/api/errors'
import { jsonError, readJsonObject } from '@/lib/api/json'
import { getCurrentUser } from '@/lib/auth/current-user'
import { commercialSignature } from '@/lib/change-order/commercial-signature'
import { validISODate } from '@/lib/projects/validation'
import { loadProjectForUser } from '@/lib/projects/data'
import { ANALYSIS_INPUT_MAX_CHARS } from '@/lib/llm/analyze-request'
import { analyzeFailureResponse, analyzeWithOpenAI } from '@/lib/llm/openai'
import { allowAnalyze } from '@/lib/llm/rate-limit'
import { supportedClientLanguage } from '@/lib/client-language'

export async function POST(request: Request) {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)
  const body = await readJsonObject(request)
  if (!body || typeof body.projectId !== 'string' || typeof body.request !== 'string' || !body.request.trim()) return jsonError(ERROR_CODES.requestBodyInvalid, 400)
  if (body.endDate !== undefined && (typeof body.endDate !== 'string' || !validISODate(body.endDate))) return jsonError(ERROR_CODES.requestBodyInvalid, 400)
  const documentLanguage = supportedClientLanguage(body.documentLanguage)
  if (body.documentLanguage !== undefined && !documentLanguage) return jsonError(ERROR_CODES.clientLanguageUnsupported, 400)
  let project = await loadProjectForUser(body.projectId, user.id)
  if (!project) return jsonError(ERROR_CODES.projectNotFound, 404)
  const locale = await getLocale()
  if (!isLocale(locale)) return jsonError(ERROR_CODES.localeInvalid, 400)
  try { project = await generationProject(user.id, body, project, locale) }
  catch { return jsonError(ERROR_CODES.draftProofInvalid, 400) }
  if (typeof body.endDate === 'string' && project.startDate && body.endDate < project.startDate) return jsonError(ERROR_CODES.requestBodyInvalid, 400)
  const termsComplete = !!project.startDate && !!project.pricingModel && !!project.currency && !!(project.hourlyRate || project.fixedPrice)
  if (!termsComplete) return jsonError(ERROR_CODES.pricingModelInvalid, 400)
  if (project.scope.length + body.request.length > ANALYSIS_INPUT_MAX_CHARS) return jsonError(ERROR_CODES.analysisInputTooLarge, 400)
  if (!allowAnalyze(user.id, Date.now())) return jsonError(ERROR_CODES.analysisRateLimited, 429)
  const draftCreatedAt = new Date().toISOString()
  try {
    const result = await analyzeWithOpenAI({
      scope: project.scope, request: body.request.trim(), industry: project.industry, locale,
      pricingModel: project.pricingModel, currency: project.currency, hourlyRate: project.hourlyRate,
      fixedPrice: project.fixedPrice, startDate: project.startDate,
      endDate: typeof body.endDate === 'string' ? body.endDate : undefined,
      draftCreatedAt,
      documentLanguage,
    })
    if (result.verdict === 'in_scope' || !result.hasAdditionalWork) return jsonError(ERROR_CODES.analysisInvalid, 409)
    if (!result.estimateValid || result.changeOrder.currency !== project.currency) return jsonError(ERROR_CODES.analysisInvalid, 502)
    result.draftCreatedAt = draftCreatedAt
    result.commercialSignature = commercialSignature(project, typeof body.endDate === 'string' ? body.endDate : undefined)
    return NextResponse.json({ result })
  } catch (error) {
    const mapped = analyzeFailureResponse(error instanceof Error ? error.message : 'unknown')
    return jsonError(mapped.error, mapped.status)
  }
}
