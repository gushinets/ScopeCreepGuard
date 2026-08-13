import { NextResponse } from 'next/server'

export function jsonError(message: string, status: number) {
  return NextResponse.json({ error: message }, { status })
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
