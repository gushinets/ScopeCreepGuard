import { expect, it } from 'vitest'
import { WorkflowOperations } from './operations'

it('retries uncertain actions with frozen parameters and starts a new operation for changed inputs', async () => {
  const sent: Array<Record<string, unknown>> = []
  let offline = true
  const operations = new WorkflowOperations(async (_path, body) => {
    sent.push(body)
    if (offline) throw new Error('offline')
    return { ok: true }
  })
  await expect(operations.run('regenerate', { expectedRevision: '2' })).rejects.toThrow('offline')
  offline = false
  await operations.run('regenerate', { expectedRevision: '2' })
  expect(sent[1]).toEqual(sent[0])
  await operations.run('regenerate', { expectedRevision: '3' })
  expect(sent[2].operationId).not.toBe(sent[0].operationId)
})
