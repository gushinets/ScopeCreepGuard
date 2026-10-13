import { expect, it, vi } from 'vitest'
import { ERROR_CODES } from '@/lib/api/errors'
import { WorkflowApiError, workflowApi } from './workflow-client'

const operationId = '11111111-1111-4111-8111-111111111111'
const pending = () => ({ operationId, statusUrl: `/api/v2/llm-operations/${operationId}`, deadlineAt: new Date(Date.now() + 180000).toISOString() })

it('polls read-only status after 202 and returns the existing successful envelope', async () => {
  vi.useFakeTimers()
  let gets = 0
  const provider = vi.fn(async (_url: string, init?: RequestInit) => {
    if (init?.method === 'POST') return Response.json(pending(), { status: 202 })
    return Response.json(++gets === 1 ? { status: 'running', result: null, error: null } : { status: 'succeeded', result: { draft: { id: 'd1' } }, error: null })
  })
  vi.stubGlobal('fetch', provider)
  const result = workflowApi('drafts/d1/regenerate', { operationId })
  await vi.runAllTimersAsync()
  await expect(result).resolves.toEqual({ draft: { id: 'd1' } })
  expect(provider.mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(1)
  expect(gets).toBe(2)
  vi.useRealTimers(); vi.unstubAllGlobals()
})

it('marks exhausted validation as terminal without presenting partial output', async () => {
  vi.stubGlobal('fetch', vi.fn(async (_url: string, init?: RequestInit) => Response.json(init?.method === 'POST' ? pending() : { status: 'failed', result: null, error: { code: ERROR_CODES.semanticAttemptsExhausted, status: 502 } }, { status: init?.method === 'POST' ? 202 : 200 })))
  await expect(workflowApi('drafts/d1/translate', { operationId })).rejects.toEqual(new WorkflowApiError(ERROR_CODES.semanticAttemptsExhausted, 502, true))
  vi.unstubAllGlobals()
})

it('preserves the Draft document-size error returned by the workflow API', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => Response.json(
    { error: ERROR_CODES.documentTooLarge },
    { status: 413 },
  )))

  await expect(workflowApi('drafts/d1', { changes: {} }, 'PUT')).rejects.toEqual(
    new WorkflowApiError(ERROR_CODES.documentTooLarge, 413),
  )
  vi.unstubAllGlobals()
})
