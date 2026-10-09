import { ERROR_CODES, isErrorCode, type ErrorCode } from './errors'

export class ApiClientError extends Error {
  constructor(public readonly code: ErrorCode, public readonly status: number) {
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
  if (!response.ok) {
    let code: ErrorCode = ERROR_CODES.requestFailed
    try {
      const body: unknown = await response.json()
      if (body && typeof body === 'object' && 'error' in body &&
        typeof body.error === 'string' && isErrorCode(body.error)) code = body.error
    } catch { /* Gateway responses can be HTML or empty. */ }
    throw new ApiClientError(code, response.status)
  }
  return response
}

export async function apiJson<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const response = await apiFetch(path, init)
  try { return await response.json() as T }
  catch { throw new ApiClientError(ERROR_CODES.requestFailed, response.status) }
}
