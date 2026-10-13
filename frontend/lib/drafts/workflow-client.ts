import { ERROR_CODES, isErrorCode, type ErrorCode } from '@/lib/api/errors'

export class WorkflowApiError extends Error {
  constructor(public code: ErrorCode, public status: number) { super(code) }
}

export async function workflowApi<T>(path: string, body?: unknown, method = body === undefined ? 'GET' : 'POST'): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api/v2/${path}`, { method, cache: 'no-store', ...(body === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }) })
  } catch { throw new WorkflowApiError(ERROR_CODES.requestFailed, 0) }
  const value = await response.json()
  if (!response.ok) throw new WorkflowApiError(isErrorCode(value.error) ? value.error : ERROR_CODES.requestFailed, response.status)
  return value as T
}
