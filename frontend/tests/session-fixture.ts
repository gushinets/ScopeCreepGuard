/** Test-only encoder of the pre-migration JOSE format. Python owns session issuance. */
import { SignJWT } from 'jose'
import { getAuthSecret, SESSION_MAX_AGE_SECONDS, type SessionUser } from '@/lib/auth/session'

export async function createSessionToken(user: SessionUser) {
  return new SignJWT({ email: user.email }).setProtectedHeader({ alg: 'HS256' })
    .setSubject(user.id).setIssuedAt().setExpirationTime(`${SESSION_MAX_AGE_SECONDS}s`)
    .sign(getAuthSecret())
}
