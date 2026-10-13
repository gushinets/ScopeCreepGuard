import { afterEach, describe, expect, it, vi } from 'vitest'
import { DraftAutosave, parseRecoveryBuffer } from './autosave'

const draft = () => ({ id: 'draft', projectId: 'project', revision: '1', requestText: '', analysisIsStale: true, lastAnalysisRunId: null, draftDocument: { version: 2 as const, reply: { text: '', tone: 'neutral' as const, language: 'en', generated: { warm: '', neutral: '', firm: '' } }, changeOrder: null }, createdAt: '', updatedAt: '', analysisRun: null })

afterEach(() => vi.useRealTimers())

it('rejects malformed recovery state instead of importing it over confirmed work', () => {
  expect(parseRecoveryBuffer({ version: 1, draftId: 'draft', baseRevision: '1', changes: {} }, 'draft')).toBeNull()
  expect(parseRecoveryBuffer({ version: 1, draftId: 'other', baseRevision: '1', changes: { requestText: 'x', draftDocument: draft().draftDocument }, attempt: null }, 'draft')).toBeNull()
  expect(parseRecoveryBuffer({ version: 1, draftId: 'draft', baseRevision: '1', changes: { requestText: 'saved locally', draftDocument: draft().draftDocument }, attempt: null }, 'draft')?.changes.requestText).toBe('saved locally')
})

describe('serialized Draft autosave', () => {
  it('reapplies edited fields onto reviewed server generation provenance', async () => {
    const original = draft()
    const saver = new DraftAutosave(original, async body => ({ ...original, ...body.changes, revision: '4' }))
    saver.edit({ requestText: 'my request', draftDocument: { ...original.draftDocument, reply: { ...original.draftDocument.reply, text: 'my edited reply' } } })
    const server = { ...original, revision: '3', draftDocument: { ...original.draftDocument, reply: { ...original.draftDocument.reply, text: 'server reply', language: 'ru', generated: { warm: 'new warm', neutral: 'new neutral', firm: 'new firm' } } } }
    saver.resolve(server, true)
    expect(saver.local.draftDocument.reply.generated).toEqual(server.draftDocument.reply.generated)
    expect(saver.local.draftDocument.reply.language).toBe('ru')
    expect(saver.local.draftDocument.reply.text).toBe('my edited reply')
    expect(saver.local.requestText).toBe('my request')
    saver.dispose()
  })
  it('recovers newer edits behind an uncertain older save without acknowledging them early', async () => {
    const original = draft()
    const oldChanges = { requestText: 'A', draftDocument: original.draftDocument }
    const newerChanges = { requestText: 'B', draftDocument: original.draftDocument }
    const sent: string[] = []
    const saver = new DraftAutosave(original, async body => {
      sent.push(body.changes.requestText)
      return { ...original, ...body.changes, revision: String(sent.length + 1) }
    })
    saver.recover({ version: 1, draftId: original.id, baseRevision: '1', changes: newerChanges,
      attempt: { generation: 1, body: { expectedRevision: '1', operationId: crypto.randomUUID(), changes: oldChanges, reason: 'autosave' } } })
    await saver.flush()
    expect(sent).toEqual(['A', 'B'])
    expect(saver.local.requestText).toBe('B')
    expect(saver.status).toBe('saved')
    saver.dispose()
  })
  it('debounces typing and saves during continuous input at the maximum interval', async () => {
    vi.useFakeTimers()
    const requests: string[] = []
    const saver = new DraftAutosave(draft(), async (body) => {
      requests.push(body.changes.requestText)
      return { ...draft(), revision: String(requests.length + 1), ...body.changes }
    })
    for (let index = 0; index < 11; index++) {
      saver.edit({ requestText: String(index) })
      await vi.advanceTimersByTimeAsync(500)
    }
    expect(requests[0]).toBe('9')
    await saver.flush()
    expect(requests.at(-1)).toBe('10')
    expect(saver.status).toBe('saved')
    saver.dispose()
  })

  it('keeps newer local text when an old response arrives and queues its next save', async () => {
    let finish: ((value: ReturnType<typeof draft>) => void) | undefined
    const bodies: Array<{ operationId: string; expectedRevision: string; changes: { requestText: string } }> = []
    const saver = new DraftAutosave(draft(), async body => {
      bodies.push(body)
      if (bodies.length === 1) return await new Promise(resolve => { finish = resolve })
      return { ...draft(), revision: '3', ...body.changes }
    })
    saver.edit({ requestText: 'first' })
    const flush = saver.flush()
    saver.edit({ requestText: 'second' })
    finish!({ ...draft(), revision: '2', requestText: 'first' })
    await flush
    expect(saver.local.requestText).toBe('second')
    expect(bodies[1].expectedRevision).toBe('2')
    expect(bodies[1].changes.requestText).toBe('second')
    saver.dispose()
  })

  it('retries an uncertain operation identically and preserves conflicting edits', async () => {
    const bodies: unknown[] = []
    let failure = true
    const saver = new DraftAutosave(draft(), async body => {
      bodies.push(structuredClone(body))
      if (failure) throw new Error('offline')
      return { ...draft(), revision: '2', ...body.changes }
    })
    saver.edit({ requestText: 'keep me' })
    await expect(saver.flush()).rejects.toThrow('offline')
    expect(saver.status).toBe('failed')
    failure = false
    await saver.flush()
    expect(bodies[1]).toEqual(bodies[0])
    saver.edit({ requestText: 'local conflict' })
    saver.save = async () => { throw Object.assign(new Error('conflict'), { status: 409 }) }
    await expect(saver.flush()).rejects.toThrow('conflict')
    expect(saver.status).toBe('conflict')
    expect(saver.local.requestText).toBe('local conflict')
    saver.resolve({ ...draft(), revision: '9', requestText: 'server text' }, true)
    expect(saver.local.requestText).toBe('local conflict')
    expect(saver.confirmed.revision).toBe('9')
    saver.dispose()
  })
})
