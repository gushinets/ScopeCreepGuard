import { hash } from 'bcryptjs'
import { eq } from 'drizzle-orm'
import { NextResponse, type NextRequest } from 'next/server'
import { ERROR_CODES } from '@/lib/api/errors'
import { db } from '@/lib/db'
import { users } from '@/lib/db/schema'
import { jsonError, readJsonObject } from '@/lib/api/json'
import {
  SESSION_COOKIE_NAME,
  SESSION_MAX_AGE_SECONDS,
  createSessionToken,
} from '@/lib/auth/session'
import { parseCredentials } from '@/lib/auth/validation'

export async function POST(request: NextRequest) {
  const body = await readJsonObject(request)
  if (!body) return jsonError(ERROR_CODES.requestBodyInvalid, 400)

  const parsed = parseCredentials({
    email: body.email,
    password: body.password,
  })
  if (!parsed.ok) return jsonError(parsed.error, 400)

  const [existingUser] = await db
    .select({ id: users.id })
    .from(users)
    .where(eq(users.email, parsed.credentials.email))
    .limit(1)

  if (existingUser) {
    return jsonError(ERROR_CODES.duplicateEmail, 409)
  }

  const { credentials } = parsed
  const passwordHash = await hash(credentials.password, 12)
  const [user] = await db
    .insert(users)
    .values({
      email: credentials.email,
      passwordHash,
    })
    .returning({ id: users.id, email: users.email })

  if (!user) {
    console.error(JSON.stringify({ event: 'auth_register_insert_missing' }))
    throw new Error('User was not created.')
  }

  const token = await createSessionToken(user)
  const response = NextResponse.json({ user }, { status: 201 })
  response.cookies.set(SESSION_COOKIE_NAME, token, {
    httpOnly: true,
    maxAge: SESSION_MAX_AGE_SECONDS,
    path: '/',
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
  })

  return response
}
