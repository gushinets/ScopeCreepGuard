import { expect, it, vi } from 'vitest'
import { WorkflowOperations } from './operations'

it('retains the uncertain command through session expiry and reauthentication', async () => {
  const bodies: Array<Record<string, unknown>> = []
  let status = 0
  const operations = new WorkflowOperations(async (_path, body) => {
    bodies.push(body)
    if (status !== 200) throw Object.assign(new Error('unconfirmed'), { status })
    return { ok: true }
  })
  await expect(operations.run('drafts/d1/analyses', { expectedRevision: '3' })).rejects.toThrow()
  status = 401
  await expect(operations.run('drafts/d1/analyses', { expectedRevision: '3' })).rejects.toThrow()
  status = 200
  await operations.run('drafts/d1/analyses', { expectedRevision: '3' })
  expect(bodies[2]).toEqual(bodies[0])
})

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

it('retains a command through reload and isolates recovery by owner', async () => {
  const storage = new Map<string, string>()
  vi.stubGlobal('sessionStorage', { getItem: (key: string) => storage.get(key) ?? null, setItem: (key: string, value: string) => storage.set(key, value) })
  const first: Array<Record<string, unknown>> = []
  const initial = new WorkflowOperations(async (_path, body) => { first.push(body); throw new Error('offline') }, 'owner-a')
  await expect(initial.run('drafts/d1/analyses', { expectedRevision: '3', locale: 'ru' })).rejects.toThrow()
  const retried: Array<Record<string, unknown>> = []
  const reloaded = new WorkflowOperations(async (_path, body) => { retried.push(body); return { applied: true } }, 'owner-a')
  await reloaded.resume('drafts/d1/')
  expect(retried).toEqual(first)
  const other = new WorkflowOperations(async () => { throw new Error('must not send') }, 'owner-b')
  expect(await other.resume('drafts/d1/')).toEqual([])
  vi.unstubAllGlobals()
})
