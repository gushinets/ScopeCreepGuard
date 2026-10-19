import { ERROR_CODES, isErrorCode, type ErrorCode } from '@/shared/api/errors'
import { apiFetch, ApiClientError } from '@/shared/api/client'

export class WorkflowApiError extends ApiClientError {
  constructor(code: ErrorCode, status: number, terminal = false, fields?: Record<string, string>, headers?: Headers) { super(code, status, terminal, fields, headers) }
}

export async function operationApi<T>(url: string, body?: unknown, method = body === undefined ? 'GET' : 'POST', signal?: AbortSignal): Promise<T> {
  let response: Response
  try {
    response = await apiFetch(url, { method, cache: 'no-store', ...(signal ? { signal } : {}), ...(body === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }) })
  } catch (failure) {
    if (failure instanceof ApiClientError) throw new WorkflowApiError(failure.code, failure.status, failure.terminal, failure.fields, failure.headers)
    throw new WorkflowApiError(ERROR_CODES.requestFailed, 0)
  }
  let value
  try { value = await response.json() }
  catch { throw new WorkflowApiError(ERROR_CODES.requestFailed, response.ok ? 0 : response.status) }
  if (response.status === 202 && value.operationId && value.statusUrl) return pollOperation<T>(value)
  return value as T
}

type Pending = { operationId: string; statusUrl: string; deadlineAt: string }
export async function pollOperation<T>(operation: Pending): Promise<T> {
  if (!/^\/api\/v2\/llm-operations\/[a-f0-9-]{36}$/i.test(operation.statusUrl) || !Number.isFinite(Date.parse(operation.deadlineAt))) throw new WorkflowApiError(ERROR_CODES.requestFailed, 0)
  while (true) {
    const value = await operationApi<{ status: string; result: T | null; error: { code: unknown; status: number } | null }>(operation.statusUrl)
    if (value.status === 'succeeded' && value.result !== null) return value.result
    const code = value.error?.code
    if (value.status === 'failed') throw new WorkflowApiError(isErrorCode(code) ? code : ERROR_CODES.requestFailed, value.error?.status ?? 502, true)
    if (Date.now() > Date.parse(operation.deadlineAt) + 5000) throw new WorkflowApiError(ERROR_CODES.operationDeadlineExceeded, 0)
    await new Promise(resolve => setTimeout(resolve, 2000))
  }
}

export async function workflowApi<T>(path: string, body?: unknown, method = body === undefined ? 'GET' : 'POST', signal?: AbortSignal): Promise<T> {
  return operationApi(`/api/v2/${path}`, body, method, signal)
}
