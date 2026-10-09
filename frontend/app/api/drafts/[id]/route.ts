import { NextResponse } from 'next/server'
import { getCurrentUser } from '@/lib/auth/current-user'
import { ERROR_CODES } from '@/lib/api/errors'
import { jsonError, readJsonObject } from '@/lib/api/json'
import { loadDraftForUser, updateDraftForUser } from '@/lib/drafts/data'
import { parseDraftDocument, validDraftId } from '@/lib/drafts/validation'

interface Context { params: Promise<{ id: string }> }
export async function GET(_request: Request, { params }: Context) {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)
  const { id } = await params
  if (!validDraftId(id)) return jsonError(ERROR_CODES.draftNotFound, 404)
  try {
    const draft = await loadDraftForUser(id, user.id)
    if (!draft) return jsonError(ERROR_CODES.draftNotFound, 404)
    return NextResponse.json({ draft }, { headers: { 'Cache-Control': 'private, no-store' } })
  } catch { return jsonError(ERROR_CODES.draftLoadFailed, 500) }
}
export async function PUT(request: Request, { params }: Context) {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)
  const { id } = await params
  if (!validDraftId(id)) return jsonError(ERROR_CODES.draftNotFound, 404)
  try {
    const saved = await loadDraftForUser(id, user.id)
    if (!saved) return jsonError(ERROR_CODES.draftNotFound, 404)
    const body = await readJsonObject(request)
    let document
    try { document = parseDraftDocument(body?.draftDocument, saved.locale, saved.analysisSnapshot) }
    catch { return jsonError(ERROR_CODES.requestBodyInvalid, 400) }
    const draft = await updateDraftForUser(id, user.id, document)
    if (!draft) return jsonError(ERROR_CODES.draftNotFound, 404)
    return NextResponse.json({ draft })
  } catch {
    console.error(JSON.stringify({ event: 'draft_update_failed', userId: user.id, draftId: id }))
    return jsonError(ERROR_CODES.draftSaveFailed, 500)
  }
}
