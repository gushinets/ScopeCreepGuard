import { ERROR_CODES, isErrorCode, type ErrorCode } from '@/shared/api/errors'

export class ApiClientError extends Error {
  constructor(public readonly code: ErrorCode, public readonly status: number,
    public readonly terminal = false, public readonly fields?: Record<string, string>,
    public readonly headers = new Headers()) {
    super(code)
  }
}

/** One request to the public same-origin API. Callers retain workflow ownership. */
export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  if (!path.startsWith('/api/') || /[\\\r\n]/.test(path) ||
    !new URL(path, 'https://same-origin.test').pathname.startsWith('/api/')) {
    throw new ApiClientError(ERROR_CODES.requestFailed, 0)
  }
  const response = await fetch(path, { ...init, credentials: 'same-origin' })
  if (response.status === 401 && !path.startsWith('/api/auth/') && typeof window !== 'undefined') {
    window.dispatchEvent(new Event('scg:session-expired'))
  }
  if (!response.ok) {
    let code: ErrorCode = ERROR_CODES.requestFailed
    let terminal = false
    let fields: Record<string, string> | undefined
    try {
      const body: unknown = await response.json()
      if (body && typeof body === 'object' && 'error' in body &&
        typeof body.error === 'string' && isErrorCode(body.error)) code = body.error
      if (body && typeof body === 'object') {
        terminal = 'operationId' in body && typeof body.operationId === 'string'
        if ('fields' in body && body.fields && typeof body.fields === 'object' && !Array.isArray(body.fields)) {
          fields = Object.fromEntries(Object.entries(body.fields).filter((entry): entry is [string, string] => typeof entry[1] === 'string'))
        }
      }
    } catch { /* Gateway responses can be HTML or empty. */ }
    throw new ApiClientError(code, response.status, terminal, fields, response.headers)
  }
  return response
}

export async function apiJson<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(path, init)
  try { return await response.json() as T }
  catch { throw new ApiClientError(ERROR_CODES.requestFailed, response.status) }
}
