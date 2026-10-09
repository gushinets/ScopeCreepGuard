import { NextResponse } from 'next/server'
import type { ErrorCode } from './errors'

export function jsonError(error: ErrorCode, status: number) {
  return NextResponse.json({ error }, { status })
}

export async function readJsonObject(request: Request) {
  try {
    const body = await request.json()
    if (!body || typeof body !== 'object' || Array.isArray(body)) {
      return null
    }
    return body as Record<string, unknown>
  } catch (error) {
    console.error(
      JSON.stringify({
        event: 'request_json_invalid',
        message: error instanceof Error ? error.message : 'Unknown JSON parse error',
      }),
    )
    return null
  }
}
