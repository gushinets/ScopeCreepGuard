import { cookies } from 'next/headers'
import { eq } from 'drizzle-orm'
import { db } from '@/lib/db'
import { users } from '@/lib/db/schema'
import { SESSION_COOKIE_NAME, verifySessionToken, type SessionUser } from './session'

export async function getCurrentUser(): Promise<SessionUser | null> {
  const cookieStore = await cookies()
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value
  if (!token) return null

  const sessionUser = await verifySessionToken(token)
  if (!sessionUser) return null

  const [user] = await db
    .select({ id: users.id, email: users.email })
    .from(users)
    .where(eq(users.id, sessionUser.id))
    .limit(1)

  if (!user) {
    console.error(
      JSON.stringify({
        event: 'auth_session_user_missing',
        userId: sessionUser.id,
      }),
    )
    return null
  }

  return user
}

export async function requireCurrentUser() {
  const user = await getCurrentUser()
  if (!user) {
    throw new Error('Authentication is required.')
  }
  return user
}
