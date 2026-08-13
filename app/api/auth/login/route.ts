import { compare } from 'bcryptjs'
import { eq } from 'drizzle-orm'
import { NextResponse, type NextRequest } from 'next/server'
import { jsonError, readJsonObject } from '@/lib/api/json'
import {
  SESSION_COOKIE_NAME,
  SESSION_MAX_AGE_SECONDS,
  createSessionToken,
} from '@/lib/auth/session'
import { parseCredentials } from '@/lib/auth/validation'
import { db } from '@/lib/db'
import { users } from '@/lib/db/schema'

export async function POST(request: NextRequest) {
  const body = await readJsonObject(request)
  if (!body) return jsonError('Request body must be a JSON object.', 400)

  const parsed = parseCredentials({
    email: body.email,
    password: body.password,
  })
  if (!parsed.ok) return jsonError(parsed.error, 400)

  const [userWithPassword] = await db
    .select({
      id: users.id,
      email: users.email,
      passwordHash: users.passwordHash,
    })
    .from(users)
    .where(eq(users.email, parsed.credentials.email))
    .limit(1)

  if (!userWithPassword) {
    return jsonError('Invalid email or password.', 401)
  }

  const isPasswordValid = await compare(
    parsed.credentials.password,
    userWithPassword.passwordHash,
  )

  if (!isPasswordValid) {
    return jsonError('Invalid email or password.', 401)
  }

  const user = {
    id: userWithPassword.id,
    email: userWithPassword.email,
  }
  const token = await createSessionToken(user)
  const response = NextResponse.json({ user })
  response.cookies.set(SESSION_COOKIE_NAME, token, {
    httpOnly: true,
    maxAge: SESSION_MAX_AGE_SECONDS,
    path: '/',
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
  })

  return response
}
