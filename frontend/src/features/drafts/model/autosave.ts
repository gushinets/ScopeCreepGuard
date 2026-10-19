import { recoveryStorage } from '@/shared/storage/browser'
import type { WorkingDocument, WorkingDraft } from '@/features/drafts/model/workflow-types'
import { applyUserPatch, isUserPatch, userPatch, type UserPatch } from '@/features/drafts/model/user-patch'

export type SaveStatus = 'saved' | 'dirty' | 'saving' | 'failed' | 'conflict'
export type SaveReason = 'autosave' | 'manual_save' | 'tone_change' | 'language_change' | 'change_order_edit'
export interface SaveBody {
  expectedRevision: string
  operationId: string
  changes: { requestText: string; draftDocument: WorkingDocument }
  patch?: UserPatch
  reason: SaveReason
}
interface Attempt { body: SaveBody; generation: number }
export interface RecoveryBuffer {
  writerId?: string
  writtenAt?: number
  version: 1; draftId: string; baseRevision: string
  changes: SaveBody['changes']; attempt: Attempt | null
  pendingPatch?: UserPatch
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value)
}

/** Apply only fields changed in the editor to a newer server document. */
function rebaseDocument(base: unknown, local: unknown, server: unknown): unknown {
  if (Object.is(local, base)) return structuredClone(server)
  if (!isRecord(base) || !isRecord(local) || !isRecord(server)) return structuredClone(local)
  const merged = structuredClone(server)
  for (const key of new Set([...Object.keys(base), ...Object.keys(local)])) {
    if (!(key in local)) delete merged[key]
    else merged[key] = rebaseDocument(base[key], local[key], server[key])
  }
  return merged
}

export function parseRecoveryBuffer(value: unknown, draftId: string): RecoveryBuffer | null {
  const object = (item: unknown): item is Record<string, unknown> => !!item && typeof item === 'object' && !Array.isArray(item)
  const changesValid = (item: unknown) => {
    if (!object(item) || typeof item.requestText !== 'string' || item.requestText.length > 100_000 || !object(item.draftDocument)) return false
    const document = item.draftDocument
    if (document.version !== 2 || !object(document.reply)) return false
    const reply = document.reply
    if (typeof reply.text !== 'string' || !['warm', 'neutral', 'firm'].includes(String(reply.tone)) || typeof reply.language !== 'string' || !object(reply.generated)) return false
    if (!['warm', 'neutral', 'firm'].every(tone => typeof (reply.generated as Record<string, unknown>)[tone] === 'string')) return false
    if (document.changeOrder !== null) {
      if (!object(document.changeOrder)) return false
      const order = document.changeOrder
      if (typeof order.language !== 'string' || typeof order.noAdditionalCharge !== 'boolean') return false
      const fields = ['description', 'estimatedHours', 'additionalCost', 'currency', 'timelineImpact', 'rationale', 'note', 'providerName', 'clientName', 'clientEmail', 'endDate', 'additionalTerms', 'clientApproverName', 'approvalDate', 'projectName', 'createdAt']
      if (!fields.every(field => typeof order[field] === 'string')) return false
    }
    return true
  }
  if (!object(value) || value.version !== 1 || value.draftId !== draftId || typeof value.baseRevision !== 'string' || !/^[1-9][0-9]{0,18}$/.test(value.baseRevision) || !changesValid(value.changes)) return null
  if (value.pendingPatch !== undefined && !isUserPatch(value.pendingPatch)) return null
  if (value.attempt !== null) {
    if (!object(value.attempt) || !object(value.attempt.body)) return null
    const body = value.attempt.body
    if (body.patch !== undefined && !isUserPatch(body.patch)) return null
    const revisionValid = typeof body.expectedRevision === 'string' && /^[1-9][0-9]{0,18}$/.test(body.expectedRevision)
    // A recovered uncertain patch retains its original command/revision even
    // after loading a newer canonical Draft. Legacy snapshots remain strict.
    if (!revisionValid || (!body.patch && body.expectedRevision !== value.baseRevision) || typeof body.operationId !== 'string' || !/^[0-9a-f-]{36}$/i.test(body.operationId) || !changesValid(body.changes) || !['autosave', 'manual_save', 'tone_change', 'language_change', 'change_order_edit'].includes(String(body.reason))) return null
  }
  return structuredClone(value) as unknown as RecoveryBuffer
}

/** One writer per tab. Operation payloads are immutable across uncertain retries. */
export class DraftAutosave {
  private writerId = crypto.randomUUID()
  confirmed: WorkingDraft
  local: WorkingDraft
  status: SaveStatus = 'saved'
  error: unknown = null
  private generation = 0
  private acknowledged = 0
  private attempt: Attempt | null = null
  private pendingPatch: UserPatch = {}
  private legacyRecoveryRevision: string | null = null
  private inFlight: Promise<void> | null = null
  private debounce: ReturnType<typeof setTimeout> | null = null
  private maximum: ReturnType<typeof setTimeout> | null = null
  private disposed = false
  private reason: SaveReason = 'autosave'
  private edits = Symbol('edits')

  get editToken() { return this.edits }

  markConflict(error: unknown) {
    this.error = error
    this.status = 'conflict'
    this.stopTimers()
    this.persist()
    if (!this.disposed) this.notify()
  }

  constructor(
    draft: WorkingDraft,
    public save: (body: SaveBody) => Promise<WorkingDraft>,
    private notify: () => void = () => {},
    private recoveryKey?: string,
  ) {
    this.confirmed = structuredClone(draft)
    this.local = structuredClone(draft)
  }

  edit(changes: Partial<SaveBody['changes']>, reason: SaveReason = 'autosave', immediate = false) {
    if (this.disposed) return
    this.edits = Symbol('edits')
    const updated = { ...this.local, ...structuredClone(changes) }
    const patch = userPatch(this.local, updated)
    if (!Object.keys(patch).length) return
    this.pendingPatch = { ...this.pendingPatch, ...patch }
    this.local = updated
    if (changes.requestText !== undefined && changes.requestText !== this.confirmed.requestText) this.local.analysisIsStale = true
    this.generation += 1
    this.reason = reason
    const failed = this.status === 'failed'
    if (this.status !== 'conflict' && !failed) this.status = this.inFlight ? 'saving' : 'dirty'
    this.persist()
    this.notify()
    if (this.status === 'conflict' || failed) return
    if (this.debounce) clearTimeout(this.debounce)
    this.debounce = setTimeout(() => { void this.flush().catch(() => {}) }, immediate ? 0 : 750)
    if (!this.maximum) this.maximum = setTimeout(() => { void this.flush().catch(() => {}) }, 5000)
  }

  private stopTimers() {
    if (this.debounce) clearTimeout(this.debounce)
    if (this.maximum) clearTimeout(this.maximum)
    this.debounce = this.maximum = null
  }

  async flush(): Promise<WorkingDraft> {
    this.stopTimers()
    if (this.status === 'conflict') throw this.error ?? new Error('conflict')
    while (this.acknowledged < this.generation) {
      if (!this.inFlight) {
        if (!this.attempt) {
          this.attempt = {
            generation: this.generation,
            body: {
              expectedRevision: this.confirmed.revision,
              operationId: crypto.randomUUID(),
              changes: { requestText: this.local.requestText, draftDocument: structuredClone(this.local.draftDocument) },
              patch: structuredClone(this.pendingPatch),
              reason: this.reason,
            },
          }
          this.pendingPatch = {}
        }
        this.persist()
        this.inFlight = this.send(this.attempt)
      }
      const active = this.inFlight
      try { await active } finally { if (this.inFlight === active) this.inFlight = null }
      if (this.disposed && this.acknowledged < this.generation) throw new Error('Editor closed; changes kept locally')
    }
    return this.confirmed
  }

  /**
   * A generation may finish while this tab has an unsaved edit. Its result is
   * already committed on the server, so retain that result and replay the
   * local edit on top of it. This is safe only before a competing save starts.
   */
  rebaseOperationResponse(response: WorkingDraft, sourceRevision: string) {
    if (
      this.disposed ||
      this.status !== 'dirty' ||
      this.inFlight ||
      this.attempt ||
      this.confirmed.revision !== sourceRevision ||
      BigInt(response.revision) <= BigInt(sourceRevision)
    ) return false

    const requestText = this.local.requestText === this.confirmed.requestText
      ? response.requestText
      : this.local.requestText
    const draftDocument = rebaseDocument(
      this.confirmed.draftDocument,
      this.local.draftDocument,
      response.draftDocument,
    ) as WorkingDocument
    this.confirmed = structuredClone(response)
    this.local = {
      ...structuredClone(response),
      requestText,
      draftDocument,
      analysisIsStale: response.analysisIsStale || requestText !== response.requestText,
    }
    this.error = null
    this.persist()
    this.notify()
    void this.flush().catch(() => {})
    return true
  }

  private async send(attempt: Attempt) {
    this.status = 'saving'
    this.error = null
    this.notify()
    try {
      let response!: WorkingDraft
      for (let retry = 0; ; retry++) {
        try { response = await this.save(structuredClone(attempt.body)); break }
        catch (error) {
          const status = (error as { status?: number }).status
          const transient = status === undefined || status === 0 || status === 408 || status === 429 || (status >= 500 && status <= 599)
          if (!transient || retry >= 2 || this.disposed) throw error
          await new Promise(resolve => setTimeout(resolve, [500, 1500][retry]))
          if (this.disposed) throw error
        }
      }
      this.confirmed = response
      this.acknowledged = attempt.generation
      if (this.generation === attempt.generation) this.local = structuredClone(response)
      else this.local = applyUserPatch(response, this.pendingPatch)
      this.attempt = null
      this.status = this.acknowledged === this.generation ? 'saved' : 'dirty'
      this.persist()
      if (!this.disposed) this.notify()
    } catch (error) {
      this.error = error
      const status = (error as { status?: number }).status
      if (status && status >= 400 && status < 500 && ![408, 429].includes(status) && attempt.body.patch) {
        // A definitive rejection did not apply. Retry the latest intent with a
        // fresh identity; an uncertain transport outcome keeps the original ID.
        this.pendingPatch = { ...attempt.body.patch, ...this.pendingPatch }
        this.attempt = null
      }
      this.status = 'failed'
      this.stopTimers()
      this.persist()
      if (!this.disposed) this.notify()
      throw error
    }
  }

  /** Explicit user choice: discard local changes, or reapply them to the reviewed server version. */
  resolve(server: WorkingDraft, keepLocal: boolean) {
    if (this.inFlight) throw new Error('save still in progress')
    this.edits = Symbol('edits')
    const document = structuredClone(server.draftDocument)
    const local = this.local.draftDocument
    const base = this.confirmed.draftDocument
    for (const field of ['text', 'tone', 'language'] as const) {
      if (local.reply[field] !== base.reply[field]) Object.assign(document.reply, { [field]: local.reply[field] })
    }
    if (local.changeOrder === null && base.changeOrder !== null) document.changeOrder = null
    else if (local.changeOrder !== null && JSON.stringify(local.changeOrder) !== JSON.stringify(base.changeOrder)) {
      const localOrder = local.changeOrder
      const baseOrder = base.changeOrder as unknown as Record<string, unknown> | null
      document.changeOrder ??= structuredClone(localOrder)
      for (const [field, value] of Object.entries(localOrder)) {
        if (field !== 'aiValues' && JSON.stringify(value) !== JSON.stringify(baseOrder?.[field])) Object.assign(document.changeOrder, { [field]: value })
      }
      // Provenance comes from the reviewed server version, not the conflicting tab.
      if (server.draftDocument.changeOrder?.aiValues) document.changeOrder.aiValues = structuredClone(server.draftDocument.changeOrder.aiValues)
      else delete document.changeOrder.aiValues
    }
    const edits = { requestText: this.local.requestText !== this.confirmed.requestText ? this.local.requestText : server.requestText, draftDocument: document }
    this.confirmed = structuredClone(server)
    this.local = structuredClone(server)
    this.attempt = null
    this.pendingPatch = {}
    this.legacyRecoveryRevision = null
    this.generation = this.acknowledged = 0
    this.status = 'saved'
    this.error = null
    if (keepLocal) this.edit(edits, 'manual_save')
    else { this.persist(); this.notify() }
  }

  recover(buffer: RecoveryBuffer) {
    if (this.inFlight) throw new Error('Save in progress')
    if (!parseRecoveryBuffer(buffer, this.confirmed.id)) throw new Error('invalid recovery Draft')
    if (!buffer.pendingPatch && buffer.baseRevision !== this.confirmed.revision) {
      // A legacy snapshot cannot distinguish user intent from stale untouched
      // fields. Preserve its original revision through persistence and reload;
      // only explicit resolution against reviewed state may derive a patch.
      this.stopTimers()
      this.edits = Symbol('edits')
      this.legacyRecoveryRevision = buffer.baseRevision
      this.local = { ...structuredClone(this.confirmed), ...structuredClone(buffer.changes) }
      this.generation = 1
      this.acknowledged = 0
      this.attempt = structuredClone(buffer.attempt)
      this.pendingPatch = {}
      this.error = Object.assign(new Error('recovery conflict'), { status: 409 })
      this.status = 'conflict'
      this.persist()
      this.notify()
      return
    }
    this.edit(buffer.changes, 'manual_save')
    this.stopTimers()
    if (buffer.pendingPatch) {
      this.generation = 1
      this.acknowledged = 0
      this.status = 'dirty'
      this.error = null
      this.pendingPatch = structuredClone(buffer.pendingPatch)
      this.local = applyUserPatch(this.confirmed, { ...buffer.attempt?.body.patch, ...this.pendingPatch })
      if (buffer.attempt) {
        const queued = Object.keys(this.pendingPatch).length > 0
        if (queued) this.generation += 1
        this.attempt = { ...buffer.attempt, generation: this.generation - Number(queued) }
      }
    } else if (buffer.attempt) {
      const queued = JSON.stringify(buffer.attempt.body.changes) !== JSON.stringify(buffer.changes)
      if (queued) this.generation += 1
      this.attempt = { ...buffer.attempt, generation: this.generation - Number(queued) }
    }
    this.persist()
    this.notify()
  }

  private persist() {
    if (!this.recoveryKey || typeof localStorage === 'undefined') return
    try {
      if (this.acknowledged === this.generation) {
        const existing = JSON.parse(recoveryStorage.get(this.recoveryKey) ?? 'null') as RecoveryBuffer | null
        if (existing?.writerId === this.writerId) recoveryStorage.remove(this.recoveryKey)
      } else recoveryStorage.set(this.recoveryKey, JSON.stringify({ version: 1, writerId: this.writerId, writtenAt: Date.now(), draftId: this.confirmed.id, baseRevision: this.legacyRecoveryRevision ?? this.confirmed.revision, changes: { requestText: this.local.requestText, draftDocument: this.local.draftDocument }, attempt: this.attempt, ...(this.legacyRecoveryRevision ? {} : { pendingPatch: this.pendingPatch }) } satisfies RecoveryBuffer))
    } catch { /* Recovery is optional; confirmed state remains in PostgreSQL. */ }
  }

  dispose() { this.disposed = true; this.stopTimers() }
}
