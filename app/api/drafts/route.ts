import { NextResponse } from 'next/server'
import { getCurrentUser } from '@/lib/auth/current-user'
import { ERROR_CODES } from '@/lib/api/errors'
import { jsonError, readJsonObject } from '@/lib/api/json'
import { createDraftForUser, listDraftsForUser } from '@/lib/drafts/data'
import { parseCreateDraft } from '@/lib/drafts/validation'

export async function GET() {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)
  try {
    return NextResponse.json({ drafts: await listDraftsForUser(user.id) }, { headers: { 'Cache-Control': 'private, no-store' } })
  } catch {
    return jsonError(ERROR_CODES.draftLoadFailed, 500)
  }
}
export async function POST(request: Request) {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)
  const body = await readJsonObject(request)
  let input
  try { input = parseCreateDraft(body) }
  catch { return jsonError(ERROR_CODES.requestBodyInvalid, 400) }
  try {
    const created = await createDraftForUser(user.id, input)
    if (!created) return jsonError(ERROR_CODES.projectNotFound, 404)
    return NextResponse.json({ draft: created.draft, entry: created.entry }, { status: created.created ? 201 : 200 })
  } catch {
    console.error(JSON.stringify({ event: 'draft_create_failed', userId: user.id, projectId: input.projectId }))
    return jsonError(ERROR_CODES.draftSaveFailed, 500)
  }
}
