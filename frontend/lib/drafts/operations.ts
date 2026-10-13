/** Keeps an uncertain request's key and parameters together until acknowledgement. */
export class WorkflowOperations {
  private pending = new Map<string, Record<string, unknown>>()

  constructor(private send: (path: string, body: Record<string, unknown>, method: string) => Promise<unknown>) {}

  async run<T>(path: string, parameters: Record<string, unknown>, method = 'POST'): Promise<T> {
    const signature = JSON.stringify([method, path, parameters])
    let body = this.pending.get(signature)
    if (!body) {
      body = { ...structuredClone(parameters), operationId: crypto.randomUUID() }
      this.pending.set(signature, body)
    }
    try {
      const result = await this.send(path, structuredClone(body), method)
      this.pending.delete(signature)
      return result as T
    } catch (error) {
      const status = (error as { status?: number }).status
      if (status && status >= 400 && status < 500) this.pending.delete(signature)
      throw error
    }
  }
}
