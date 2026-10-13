import { ERROR_CODES, isErrorCode, type ErrorCode } from '@/lib/api/errors'

export class WorkflowApiError extends Error {
  constructor(public code: ErrorCode, public status: number, public terminal = false) { super(code) }
}

export async function operationApi<T>(url: string, body?: unknown, method = body === undefined ? 'GET' : 'POST'): Promise<T> {
  let response: Response
  try {
    response = await fetch(url, { method, cache: 'no-store', ...(body === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }) })
  } catch { throw new WorkflowApiError(ERROR_CODES.requestFailed, 0) }
  const value = await response.json()
  if (!response.ok) throw new WorkflowApiError(isErrorCode(value.error) ? value.error : ERROR_CODES.requestFailed, response.status, !!value.operationId)
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

export async function workflowApi<T>(path: string, body?: unknown, method = body === undefined ? 'GET' : 'POST'): Promise<T> {
  return operationApi(`/api/v2/${path}`, body, method)
}
