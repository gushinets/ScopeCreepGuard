// @vitest-environment jsdom
import { afterEach, expect, it, vi } from 'vitest'
import { DraftAutosave, parseRecoveryBuffer, type RecoveryBuffer, type SaveBody } from '@/features/drafts/model/autosave'
import { applyUserPatch } from '@/features/drafts/model/user-patch'
import type { WorkingDraft } from '@/features/drafts/model/workflow-types'

const draft = (): WorkingDraft => ({ id: 'draft', projectId: 'project', revision: '1', requestText: '', analysisIsStale: true, lastAnalysisRunId: null, draftDocument: { version: 2, reply: { text: '', tone: 'neutral', language: 'en', generated: { warm: '', neutral: '', firm: '' } }, changeOrder: null }, createdAt: '', updatedAt: '', analysisRun: null })
afterEach(() => { vi.useRealTimers(); localStorage.clear() })

it.each([false, true])('keeps stale legacy snapshots revision-bound across reloads (uncertain command: %s)', async uncertain => {
  const key = 'owner:draft:legacy'
  const stale = draft()
  stale.requestText = 'old request'
  stale.draftDocument.reply.text = 'old reply'
  const legacy: RecoveryBuffer = {
    version: 1, draftId: stale.id, baseRevision: '1',
    changes: { requestText: stale.requestText, draftDocument: stale.draftDocument },
    attempt: uncertain ? { generation: 1, body: { expectedRevision: '1', operationId: crypto.randomUUID(), changes: { requestText: stale.requestText, draftDocument: stale.draftDocument }, reason: 'autosave' } } : null,
  }
  localStorage.setItem(key, JSON.stringify(legacy))
  const server = draft()
  server.revision = '9'
  server.requestText = 'newer server request'
  server.draftDocument.reply.text = 'newer server reply'
  const save = vi.fn(async (body: SaveBody) => ({ ...applyUserPatch(server, body.patch!), revision: '10' }))
  for (let reload = 0; reload < 3; reload++) {
    const restored = parseRecoveryBuffer(JSON.parse(localStorage.getItem(key)!), 'draft')!
    const saver = new DraftAutosave(server, save, () => {}, key)
    saver.recover(restored)
    expect(saver.status).toBe('conflict')
    expect(saver.local.requestText).toBe(stale.requestText)
    expect(saver.confirmed).toEqual(server)
    await expect(saver.flush()).rejects.toThrow('recovery conflict')
    saver.edit({ draftDocument: { ...saver.local.draftDocument, reply: { ...saver.local.draftDocument.reply, text: `unresolved local edit ${reload}` } } })
    const persisted = parseRecoveryBuffer(JSON.parse(localStorage.getItem(key)!), 'draft')!
    expect(persisted.baseRevision).toBe('1')
    expect(persisted.pendingPatch).toBeUndefined()
    expect(persisted.attempt).toEqual(legacy.attempt)
    if (reload === 2) {
      // Only explicit resolution against reviewed server state may derive intent.
      saver.resolve(server, true)
      await saver.flush()
      expect(save).toHaveBeenCalledTimes(1)
      expect(save.mock.calls[0][0].expectedRevision).toBe('9')
      expect(saver.local.requestText).toBe('old request')
      expect(saver.local.draftDocument.reply.text).toBe('unresolved local edit 2')
      expect(localStorage.getItem(key)).toBeNull()
    } else expect(save).not.toHaveBeenCalled()
    saver.dispose()
  }
})

it.each([0, 503])('bounds transport retries (%s), keeps newer typing and reuses the uncertain command', async status => {
  vi.useFakeTimers()
  let fail = true
  let server = draft()
  const bodies: SaveBody[] = []
  const saver = new DraftAutosave(server, async body => {
    bodies.push(body)
    if (fail) throw Object.assign(new Error('unavailable'), { status })
    server = { ...applyUserPatch(server, body.patch!), revision: String(+server.revision + 1) }
    return server
  }, () => {}, 'owner:draft:tab')
  saver.edit({ requestText: 'first' })
  const rejected = expect(saver.flush()).rejects.toThrow('unavailable')
  await vi.advanceTimersByTimeAsync(2000)
  await rejected
  expect(bodies).toHaveLength(3)
  expect(bodies.every(body => body.operationId === bodies[0].operationId)).toBe(true)
  saver.edit({ requestText: 'newest' })
  await vi.advanceTimersByTimeAsync(30_000)
  expect(bodies).toHaveLength(3)
  expect(saver.local.requestText).toBe('newest')
  expect(saver.status).toBe('failed')
  expect(JSON.parse(localStorage.getItem('owner:draft:tab')!).changes.requestText).toBe('newest')
  fail = false
  await saver.flush()
  expect(bodies[3].operationId).toBe(bodies[0].operationId)
  expect(bodies[4].patch).toEqual({ requestText: 'newest' })
  expect(server.requestText).toBe('newest')
  expect(saver.status).toBe('saved')
  expect(localStorage.getItem('owner:draft:tab')).toBeNull()
  saver.dispose()
})

it.each([401, 400, 422])('does not automatically retry terminal HTTP %s', async status => {
  vi.useFakeTimers()
  const save = vi.fn(async () => { throw Object.assign(new Error('terminal'), { status }) })
  const saver = new DraftAutosave(draft(), save)
  saver.edit({ requestText: 'kept' })
  await expect(saver.flush()).rejects.toThrow('terminal')
  saver.edit({ requestText: 'still kept' })
  await vi.advanceTimersByTimeAsync(60_000)
  expect(save).toHaveBeenCalledTimes(1)
  expect(saver.local.requestText).toBe('still kept')
  saver.dispose()
})

it('keeps one logical save after a lost response and synchronizes unrelated canonical fields', async () => {
  vi.useFakeTimers()
  let calls = 0
  let server = draft()
  const receipt = new Set<string>()
  const saver = new DraftAutosave(server, async body => {
    if (!receipt.has(body.operationId)) {
      receipt.add(body.operationId)
      server = { ...applyUserPatch(server, body.patch!), revision: '2' }
    }
    if (++calls === 1) {
      server.draftDocument.reply.tone = 'firm' // another tab, after application
      server.revision = '3'
      throw Object.assign(new Error('lost response'), { status: 0 })
    }
    return server
  })
  saver.edit({ requestText: 'saved once' })
  const saving = saver.flush()
  expect(saver.status).toBe('saving')
  await vi.advanceTimersByTimeAsync(500)
  await saving
  expect(receipt.size).toBe(1)
  expect(saver.confirmed.revision).toBe('3')
  expect(saver.local.draftDocument.reply.tone).toBe('firm')
  saver.dispose()
})

it('manual Retry replaces a definitively rejected command with the latest corrected intent', async () => {
  let failure = true
  const bodies: SaveBody[] = []
  const saver = new DraftAutosave(draft(), async body => {
    bodies.push(body)
    if (failure) throw Object.assign(new Error('invalid'), { status: 400 })
    return { ...applyUserPatch(draft(), body.patch!), revision: '2' }
  })
  saver.edit({ requestText: 'invalid old value' })
  await expect(saver.flush()).rejects.toThrow('invalid')
  saver.edit({ requestText: 'corrected value' })
  failure = false
  await saver.flush()
  expect(bodies).toHaveLength(2)
  expect(bodies[1].operationId).not.toBe(bodies[0].operationId)
  expect(bodies[1].patch).toEqual({ requestText: 'corrected value' })
  expect(saver.local.requestText).toBe('corrected value')
  saver.dispose()
})

it('overlays only new typing on an older acknowledgement, including an explicit clear', async () => {
  let finish!: (value: WorkingDraft) => void
  const bodies: SaveBody[] = []
  const saver: DraftAutosave = new DraftAutosave(draft(), async body => {
    bodies.push(body)
    if (bodies.length === 1) return new Promise(resolve => { finish = resolve })
    return { ...applyUserPatch(saver.confirmed, body.patch!), revision: '4' }
  })
  saver.edit({ requestText: 'old' })
  const saving = saver.flush()
  saver.edit({ requestText: '' })
  const canonical = draft()
  canonical.requestText = 'old'
  canonical.revision = '3'
  canonical.draftDocument.reply.tone = 'firm'
  finish(canonical)
  await saving
  expect(bodies[1].patch).toEqual({ requestText: '' })
  expect(saver.local.requestText).toBe('')
  expect(saver.local.draftDocument.reply.tone).toBe('firm')
  saver.dispose()
})

it('recovers intent across reload and newer revisions without copying untouched old fields', async () => {
  const key = 'scg:unconfirmed:owner:draft:tab'
  const otherKey = 'scg:unconfirmed:another-owner:draft:tab'
  localStorage.setItem(otherKey, 'untouched')
  const first = new DraftAutosave(draft(), async () => draft(), () => {}, key)
  first.edit({ requestText: 'recover me' })
  first.dispose()
  const buffer = parseRecoveryBuffer(JSON.parse(localStorage.getItem(key)!), 'draft')!
  expect(parseRecoveryBuffer(buffer, 'different-draft')).toBeNull()
  const server = draft()
  server.revision = '9'
  server.draftDocument.reply.tone = 'firm'
  const second = new DraftAutosave(server, async body => ({ ...applyUserPatch(server, body.patch!), revision: '10' }), () => {}, key)
  second.recover(buffer)
  expect(second.local.requestText).toBe('recover me')
  expect(second.local.draftDocument.reply.tone).toBe('firm')
  expect(localStorage.getItem(key)).not.toBeNull()
  await second.flush()
  expect(localStorage.getItem(key)).toBeNull()
  expect(localStorage.getItem(otherKey)).toBe('untouched')
  second.dispose()
})

it('keeps an uncertain patch recoverable across repeated reloads onto newer revisions', async () => {
  vi.useFakeTimers()
  const key = 'owner:draft:reload'
  const first = new DraftAutosave(draft(), async () => { throw Object.assign(new Error('offline'), { status: 0 }) }, () => {}, key)
  first.edit({ requestText: 'uncertain' })
  const rejected = expect(first.flush()).rejects.toThrow('offline')
  await vi.advanceTimersByTimeAsync(2000)
  await rejected
  const original = parseRecoveryBuffer(JSON.parse(localStorage.getItem(key)!), 'draft')!
  first.dispose()
  const server = { ...draft(), revision: '9' }
  const second = new DraftAutosave(server, async () => server, () => {}, key)
  second.recover(original)
  second.dispose()
  const reloaded = parseRecoveryBuffer(JSON.parse(localStorage.getItem(key)!), 'draft')!
  expect(reloaded).not.toBeNull()
  expect(reloaded.attempt?.body.operationId).toBe(original.attempt?.body.operationId)
  expect(reloaded.attempt?.body.expectedRevision).toBe('1')
  expect(reloaded.baseRevision).toBe('9')
})
