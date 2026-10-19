import { tabStorage } from '@/shared/storage/browser'
/** Keeps an uncertain request's key and parameters together until acknowledgement. */
export class WorkflowOperations {
  private pending = new Map<string, Record<string, unknown>>()

  constructor(private send: (path: string, body: Record<string, unknown>, method: string) => Promise<unknown>, private owner = '') {}
  setOwner(owner: string) { if (owner !== this.owner) { this.pending.clear(); this.owner = owner } }
  private storageKey() { return this.owner ? `scg:llm-commands:${this.owner}` : null }
  private durable(path: string) { return /^drafts\/[a-z0-9-]+\/(analyses|regenerate|translate|estimate)$/i.test(path) }
  private load() {
    const key = this.storageKey()
    if (!key) return
    try {
      const entries = JSON.parse(tabStorage.get(key) ?? '[]')
      for (const [signature, body] of entries) {
        const [method, path] = JSON.parse(signature)
        if (method === 'POST' && this.durable(path) && typeof body?.operationId === 'string' && !this.pending.has(signature)) this.pending.set(signature, body)
      }
    } catch { /* In-memory keys still protect retries when browser storage is unavailable. */ }
  }
  private persist() {
    const key = this.storageKey()
    if (!key) return
    try { tabStorage.set(key, JSON.stringify([...this.pending].filter(([signature]) => this.durable(JSON.parse(signature)[1])))) }
    catch { /* The server operation survives even if local recovery storage is unavailable. */ }
  }
  async resume<T>(prefix: string): Promise<T[]> {
    this.load()
    const entries = [...this.pending].filter(([signature]) => JSON.parse(signature)[1].startsWith(prefix))
    return Promise.all(entries.map(([signature, body]) => {
      const [method, path, parameters] = JSON.parse(signature)
      this.pending.set(signature, body)
      return this.run<T>(path, parameters, method)
    }))
  }

  async run<T>(path: string, parameters: Record<string, unknown>, method = 'POST'): Promise<T> {
    const signature = JSON.stringify([method, path, parameters])
    this.load()
    let body = this.pending.get(signature)
    if (!body) {
      body = { ...structuredClone(parameters), operationId: crypto.randomUUID() }
      this.pending.set(signature, body)
      this.persist()
    }
    try {
      const result = await this.send(path, structuredClone(body), method)
      this.pending.delete(signature)
      this.persist()
      return result as T
    } catch (error) {
      const status = (error as { status?: number }).status
      if ((error as { terminal?: boolean }).terminal || status && status >= 400 && status < 500 && ![401, 403, 408, 429].includes(status)) { this.pending.delete(signature); this.persist() }
      throw error
    }
  }
}
