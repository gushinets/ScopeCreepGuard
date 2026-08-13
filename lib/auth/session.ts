import { SignJWT, jwtVerify } from 'jose'
import { JOSEError } from 'jose/errors'

export const SESSION_COOKIE_NAME = 'scg_session'
export const SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 7

export interface SessionUser {
  id: string
  email: string
}

function getAuthSecret() {
  const secret = process.env.AUTH_SECRET
  if (!secret) {
    console.error(
      JSON.stringify({
        event: 'config_missing',
        variable: 'AUTH_SECRET',
        source: 'lib/auth/session.ts',
      }),
    )
    throw new Error('AUTH_SECRET is required')
  }
  return new TextEncoder().encode(secret)
}

export async function createSessionToken(user: SessionUser) {
  return new SignJWT({ email: user.email })
    .setProtectedHeader({ alg: 'HS256' })
    .setSubject(user.id)
    .setIssuedAt()
    .setExpirationTime(`${SESSION_MAX_AGE_SECONDS}s`)
    .sign(getAuthSecret())
}

export async function verifySessionToken(token: string): Promise<SessionUser | null> {
  try {
    const { payload } = await jwtVerify(token, getAuthSecret())
    if (typeof payload.sub !== 'string' || typeof payload.email !== 'string') {
      console.error(
        JSON.stringify({
          event: 'auth_session_invalid_payload',
          hasSubject: typeof payload.sub === 'string',
          hasEmail: typeof payload.email === 'string',
        }),
      )
      return null
    }

    return {
      id: payload.sub,
      email: payload.email,
    }
  } catch (error) {
    if (error instanceof JOSEError) {
      console.error(
        JSON.stringify({
          event: 'auth_session_invalid',
          code: error.code,
        }),
      )
      return null
    }
    throw error
  }
}
