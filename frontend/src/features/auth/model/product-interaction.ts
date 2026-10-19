/** Leading-edge observations: no queued input, timers, or automatic retries. */
export function interactionObserver(
  send: (signal: AbortSignal) => unknown,
  now: () => number = () => performance.now(),
) {
  let disposed = false
  let lastAttempt: number | undefined
  let inFlight: AbortController | undefined
  const observe = (event: Pick<Event, 'isTrusted'>, hidden: boolean) => {
    if (disposed || !event.isTrusted || hidden || inFlight) return
    const timestamp = now()
    if (lastAttempt !== undefined && timestamp - lastAttempt < 30_000) return
    lastAttempt = timestamp
    const controller = new AbortController()
    inFlight = controller
    try {
      void Promise.resolve(send(controller.signal))
        .catch(() => { /* Only a later genuine interaction may retry. */ })
        .finally(() => { if (inFlight === controller) inFlight = undefined })
    } catch {
      inFlight = undefined
    }
  }
  return Object.assign(observe, {
    dispose() {
      disposed = true
      inFlight?.abort()
      inFlight = undefined
    },
  })
}
