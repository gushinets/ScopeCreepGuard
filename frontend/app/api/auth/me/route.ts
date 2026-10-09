import { NextResponse } from 'next/server'
import { ERROR_CODES } from '@/lib/api/errors'
import { jsonError } from '@/lib/api/json'
import { getCurrentUser } from '@/lib/auth/current-user'

export async function GET() {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)

  return NextResponse.json({ user })
}
