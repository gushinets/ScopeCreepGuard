import { NextResponse, type NextRequest } from 'next/server'
import { SESSION_COOKIE_NAME, verifySessionToken } from '@/lib/auth/session'

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

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  if (isStaticAsset(pathname)) {
    return NextResponse.next()
  }

  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value
  const sessionUser = token ? await verifySessionToken(token) : null
  const isPublicPage = PUBLIC_PAGE_PATHS.has(pathname)
  const isAuthApi = pathname.startsWith('/api/auth/')

  if (isAuthApi) {
    return NextResponse.next()
  }

  if (sessionUser && isPublicPage) {
    return NextResponse.redirect(new URL('/', request.url))
  }

  if (!sessionUser && pathname.startsWith('/api/')) {
    return NextResponse.json(
      { error: 'Authentication is required.' },
      { status: 401 },
    )
  }

  if (!sessionUser && !isPublicPage) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
}
