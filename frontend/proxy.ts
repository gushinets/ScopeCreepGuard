import { NextResponse, type NextRequest } from 'next/server'
import { ERROR_CODES } from '@/lib/api/errors'
import { SESSION_COOKIE_NAME, verifySessionToken } from '@/lib/auth/session'
import { allowsApiOrigin } from '@/lib/api/origin'
import { forwardToBackend } from '@/lib/api/forward'

const PUBLIC_PAGE_PATHS = new Set(['/login', '/register'])

function isStaticAsset(pathname: string) {
  return (
    pathname.startsWith('/_next/') ||
    pathname === '/favicon.ico' ||
    pathname === '/robots.txt' ||
    pathname === '/sitemap.xml' ||
    /\.[a-zA-Z0-9]+$/.test(pathname)
  )
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl

  if (!allowsApiOrigin(request)) {
    return NextResponse.json({ error: ERROR_CODES.requestFailed }, { status: 403 })
  }

  if (isStaticAsset(pathname)) {
    return NextResponse.next()
  }

  // Python authenticates draft APIs; page navigation still uses the session guard.
  if (pathname === '/api/drafts' || pathname.startsWith('/api/drafts/')) {
    return NextResponse.next()
  }

  const isPublicPage = PUBLIC_PAGE_PATHS.has(pathname)
  const isAuthApi = pathname.startsWith('/api/auth/')
  const isLocaleApi = pathname === '/api/locale'

  if (isAuthApi || isLocaleApi) {
    return NextResponse.next()
  }

  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value
  const sessionUser = token ? await verifySessionToken(token) : null

  if (sessionUser && isPublicPage) {
    const owner = await forwardToBackend(new Request(new URL('/api/auth/me', request.url), {
      headers: { cookie: request.headers.get('cookie') ?? '' },
      signal: AbortSignal.timeout(3000),
    }), '/api/auth/me')
    if (owner.status === 200) return NextResponse.redirect(new URL('/', request.url))
    // Deleted users may recover at login; an outage must not delete a valid session.
    const response = NextResponse.next()
    if (owner.status === 401) {
      for (const cookie of owner.headers.getSetCookie()) response.headers.append('set-cookie', cookie)
    }
    return response
  }

  if (!sessionUser && pathname.startsWith('/api/')) {
    return NextResponse.json(
      { error: ERROR_CODES.authRequired },
      { status: 401 },
    )
  }

  if (!sessionUser && !isPublicPage) {
    if (pathname === '/') {
      return NextResponse.rewrite(new URL('/login', request.url))
    }
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
