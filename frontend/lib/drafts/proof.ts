
import { createHmac } from 'node:crypto'
import { jwtVerify } from 'jose'
import { getAuthSecret } from '@/lib/auth/session'
import { isLocale } from '@/i18n/config'
import { parseSnapshot, validDraftId } from './validation'
import type { DraftProofClaims } from './types'

const VERSION = 'scg-draft-proof-v1'
export const DRAFT_PROOF_LIFETIME_SECONDS = 60 * 60
export class DraftProofError extends Error {
  constructor() { super('invalid_or_expired_draft_proof') }
}
function signingKey() {
  // Domain separation: session cookies cannot act as draft proofs.
  return createHmac('sha256', getAuthSecret()).update(VERSION).digest()
}
export async function verifyDraftProof(
  proof: unknown,
  expected: Pick<DraftProofClaims, 'userId' | 'projectId' | 'request' | 'locale'>,
): Promise<DraftProofClaims> {
  const key = signingKey()
  try {
    if (typeof proof !== 'string' || proof.length > 2_000_000) throw new DraftProofError()
    const { payload, protectedHeader } = await jwtVerify(proof, key, {
      algorithms: ['HS256'], issuer: 'scope-creep-guard', audience: 'draft-creation',
      typ: VERSION, requiredClaims: ['iat', 'exp', 'sub'],
    })
    const now = Math.floor(Date.now() / 1000)
    if (protectedHeader.typ !== VERSION || payload.version !== VERSION ||
      !Number.isInteger(payload.iat) || !Number.isInteger(payload.exp) ||
      payload.iat! > now || payload.exp! <= payload.iat! ||
      payload.exp! - payload.iat! > DRAFT_PROOF_LIFETIME_SECONDS ||
      payload.sub !== expected.userId || payload.userId !== expected.userId ||
      payload.projectId !== expected.projectId || payload.request !== expected.request ||
      payload.locale !== expected.locale || !validDraftId(payload.projectId) ||
      typeof payload.locale !== 'string' || !isLocale(payload.locale) ||
      !payload.projectSnapshot || typeof payload.projectSnapshot !== 'object' ||
      (payload.projectSnapshot as { version?: unknown }).version !== 1) throw new DraftProofError()
    return {
      userId: expected.userId, projectId: expected.projectId, request: expected.request, locale: expected.locale,
      analysisSnapshot: parseSnapshot(payload.analysisSnapshot, expected.locale),
      projectSnapshot: payload.projectSnapshot as DraftProofClaims['projectSnapshot'],
    }
  } catch { throw new DraftProofError() }
}
