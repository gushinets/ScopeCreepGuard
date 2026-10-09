import { NextResponse, type NextRequest } from 'next/server'
import { ERROR_CODES } from '@/lib/api/errors'
import { jsonError, readJsonObject } from '@/lib/api/json'
import { isLocale, localeCookieName } from '@/i18n/config'

const LOCALE_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365

export async function POST(request: NextRequest) {
  const body = await readJsonObject(request)
  if (!body) return jsonError(ERROR_CODES.requestBodyInvalid, 400)

  if (typeof body.locale !== 'string' || !isLocale(body.locale)) {
    return jsonError(ERROR_CODES.localeInvalid, 400)
  }

  const response = NextResponse.json({ ok: true })
  response.cookies.set(localeCookieName, body.locale, {
    httpOnly: false,
    maxAge: LOCALE_COOKIE_MAX_AGE_SECONDS,
    path: '/',
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
  })
  return response
}
