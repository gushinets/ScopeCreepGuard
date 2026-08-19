import { NextResponse } from 'next/server'
import { ERROR_CODES } from '@/lib/api/errors'
import { jsonError, readJsonObject } from '@/lib/api/json'
import { getCurrentUser } from '@/lib/auth/current-user'
import { loadHistoryForUser, upsertEvaluationCase } from '@/lib/evaluations/data'
import { parseEvaluationInput, resolveHumanVerdict } from '@/lib/evaluations/validation'

export async function POST(request: Request) {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)

  const body = await readJsonObject(request)
  if (!body) return jsonError(ERROR_CODES.requestBodyInvalid, 400)

  const parsed = parseEvaluationInput(body)
  if (!parsed.ok) return jsonError(parsed.error, parsed.status)

  const owned = await loadHistoryForUser(parsed.label.historyEntryId, user.id)
  if (!owned) return jsonError(ERROR_CODES.evaluationHistoryNotFound, 404)

  const resolved = resolveHumanVerdict(parsed.label, owned.history.verdict)
  if (!resolved.ok) return jsonError(resolved.error, 400)

  const evaluation = await upsertEvaluationCase({
    userId: user.id,
    historyEntryId: owned.history.id,
    scope: owned.project.scope,
    request: owned.history.request,
    aiVerdict: owned.history.verdict,
    humanVerdict: resolved.humanVerdict,
    aiReasoning: parsed.label.aiReasoning,
    accuracy: parsed.label.accuracy,
    industry: owned.project.industry,
  })

  return NextResponse.json({ evaluation }, { status: 200 })
}
