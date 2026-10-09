/** Match configured public origins exactly; never trust Host/forwarded headers. */
export function allowsApiOrigin(request: Request): boolean {
  const url = new URL(request.url)
  if (!url.pathname.startsWith('/api/') || !['POST', 'PUT', 'PATCH', 'DELETE'].includes(request.method)) return true
  const origin = request.headers.get('origin')
  if (origin === null) return true
  try {
    const allowed: unknown = JSON.parse(process.env.SCOPE_GUARD_ALLOWED_ORIGINS ?? '[]')
    return Array.isArray(allowed) && allowed.some((value) => {
      if (typeof value !== 'string') return false
      const parsed = new URL(value)
      return ['http:', 'https:'].includes(parsed.protocol) && !parsed.username && !parsed.password &&
        parsed.origin === value && value === origin
    })
  } catch { return false }
}
