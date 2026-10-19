import { createHmac } from 'node:crypto'
import { SignJWT } from 'jose'
import { getAuthSecret } from '@/test/session-reference'
import { parseSnapshot } from '@/test/draft-validation-reference'
import { DRAFT_PROOF_LIFETIME_SECONDS } from '@/test/draft-proof-reference'
import type { DraftProofClaims } from '@/features/drafts/model/types'

const VERSION = 'scg-draft-proof-v1'
function signingKey() {
  return createHmac('sha256', getAuthSecret()).update(VERSION).digest()
}
export async function issueDraftProof(claims: DraftProofClaims): Promise<string> {
  const analysisSnapshot = parseSnapshot(claims.analysisSnapshot, claims.locale)
  const now = Math.floor(Date.now() / 1000)
  return new SignJWT({ ...claims, analysisSnapshot, version: VERSION })
    .setProtectedHeader({ alg: 'HS256', typ: VERSION })
    .setIssuer('scope-creep-guard').setAudience('draft-creation')
    .setSubject(claims.userId).setIssuedAt(now)
    .setExpirationTime(now + DRAFT_PROOF_LIFETIME_SECONDS).sign(signingKey())
}
