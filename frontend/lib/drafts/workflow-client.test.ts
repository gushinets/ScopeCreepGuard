import { expect, it, vi } from 'vitest'
import { ERROR_CODES } from '@/lib/api/errors'
import { WorkflowApiError, workflowApi } from './workflow-client'

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
