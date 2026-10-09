import 'server-only'
import { Agent, fetch as upstreamFetch } from 'undici'
import { ERROR_CODES } from './errors'

const requestHeaders = ['cookie', 'origin', 'content-type', 'accept', 'x-request-id']
const responseHeaders = ['content-type', 'cache-control', 'content-disposition', 'location', 'retry-after', 'x-request-id']
// Cancellation belongs to the incoming request. No shorter proxy deadline than LLM retries.
const dispatcher = new Agent({ headersTimeout: 0, bodyTimeout: 0 })

/** Server-only transport for migrated handlers. No business fallback or retries. */
export async function forwardToBackend(request: Request, path?: string): Promise<Response> {
  try {
    const configured = process.env.SCOPE_GUARD_API_ORIGIN
    if (!configured) throw new Error('backend_origin_missing')
    const origin = new URL(configured)
    if (!['http:', 'https:'].includes(origin.protocol) || origin.username || origin.password ||
      origin.origin !== configured) throw new Error('backend_origin_invalid')
    const source = new URL(request.url)
    const targetPath = path ?? `${source.pathname}${source.search}`
    if (!targetPath.startsWith('/api/') || /[\\\r\n]/.test(targetPath)) throw new Error('backend_path_invalid')
    const target = new URL(targetPath, origin)
    if (target.origin !== origin.origin || !target.pathname.startsWith('/api/')) throw new Error('backend_path_invalid')
    const headers = new Headers()
    for (const key of requestHeaders) {
      const value = request.headers.get(key)
      if (value !== null) headers.set(key, value)
    }
    const upstream = await upstreamFetch(target, {
      method: request.method, headers,
      ...(request.method === 'GET' || request.method === 'HEAD' ? {} : { body: await request.arrayBuffer() }),
      signal: request.signal, redirect: 'manual', cache: 'no-store', dispatcher,
    })
    const outputHeaders = new Headers()
    for (const key of responseHeaders) {
      const value = upstream.headers.get(key)
      if (value !== null) outputHeaders.set(key, value)
    }
    for (const cookie of upstream.headers.getSetCookie()) outputHeaders.append('set-cookie', cookie)
    return new Response(upstream.body as ReadableStream<Uint8Array> | null, { status: upstream.status, headers: outputHeaders })
  } catch {
    return Response.json({ error: ERROR_CODES.requestFailed }, { status: 503 })
  }
}
