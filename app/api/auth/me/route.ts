import { NextResponse } from 'next/server'
import { jsonError } from '@/lib/api/json'
import { getCurrentUser } from '@/lib/auth/current-user'

export async function GET() {
  const user = await getCurrentUser()
  if (!user) return jsonError('Authentication is required.', 401)

  return NextResponse.json({ user })
}
