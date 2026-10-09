import { NextResponse } from 'next/server'
import { ERROR_CODES } from '@/lib/api/errors'
import { jsonError } from '@/lib/api/json'
import { getCurrentUser } from '@/lib/auth/current-user'
import { listEvaluationCasesForUser } from '@/lib/evaluations/data'
import {
  serializeEvaluationJsonl,
  toEvaluationJsonlRecord,
} from '@/lib/evaluations/export'

export async function GET() {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)

  try {
    const rows = await listEvaluationCasesForUser(user.id)
    const body = serializeEvaluationJsonl(rows.map(toEvaluationJsonlRecord))
    return new NextResponse(body, {
      status: 200,
      headers: {
        'Content-Type': 'application/x-ndjson; charset=utf-8',
        'Content-Disposition': 'attachment; filename="scope-creep-evaluations.jsonl"',
      },
    })
  } catch (error) {
    console.error(
      JSON.stringify({
        event: 'evaluation_export_failed',
        userId: user.id,
        message: error instanceof Error ? error.message : 'unknown',
      }),
    )
    throw error
  }
}
