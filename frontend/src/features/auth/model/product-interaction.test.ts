import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { interactionObserver } from '@/features/auth/model/product-interaction'

const realInput = { isTrusted: true }
const clock = () => Date.now()
function deferred() {
  let resolve!: () => void
  const promise = new Promise<void>(done => { resolve = done })
  return { promise, resolve }
}

describe('bounded product interaction observations', () => {
  beforeEach(() => { vi.useFakeTimers(); vi.setSystemTime(0) })
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks() })

  it('coalesces pointerdown + 20 paired typing events + 10 wheel events into one immediate send', () => {
    const send = vi.fn()
    const observe = interactionObserver(send, clock)
    observe(realInput, false) // pointerdown
    for (let character = 0; character < 20; character++) {
      observe(realInput, false) // keydown
      observe(realInput, false) // input
    }
    for (let wheel = 0; wheel < 10; wheel++) observe(realInput, false)
    expect(send).toHaveBeenCalledTimes(1)
  })

  it('sustains periodic observations during two minutes of continuous interaction', async () => {
    const send = vi.fn()
    const observe = interactionObserver(send, clock)
    observe(realInput, false)
    for (let second = 1; second <= 120; second++) {
      await vi.advanceTimersByTimeAsync(1_000)
      observe(realInput, false)
      observe(realInput, false)
    }
    expect(send).toHaveBeenCalledTimes(5) // 0,30,60,90,120 seconds
    await vi.advanceTimersByTimeAsync(600_000)
    expect(send).toHaveBeenCalledTimes(5)
    expect(vi.getTimerCount()).toBe(0)
  })

  it('waits the full 30 seconds between attempts without scheduling trailing input', async () => {
    const send = vi.fn()
    const observe = interactionObserver(send, clock)
    observe(realInput, false)
    await vi.advanceTimersByTimeAsync(29_999)
    observe(realInput, false)
    expect(send).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(1)
    expect(send).toHaveBeenCalledTimes(1)
    observe(realInput, false)
    expect(send).toHaveBeenCalledTimes(2)
  })

  it('never overlaps slow requests or queues a send for when they settle', async () => {
    const pending = deferred()
    const send = vi.fn(() => pending.promise)
    const observe = interactionObserver(send, clock)
    observe(realInput, false)
    for (let minute = 0; minute < 3; minute++) {
      await vi.advanceTimersByTimeAsync(60_000)
      observe(realInput, false)
    }
    expect(send).toHaveBeenCalledTimes(1)
    pending.resolve()
    await vi.advanceTimersByTimeAsync(0)
    expect(send).toHaveBeenCalledTimes(1)
    observe(realInput, false)
    expect(send).toHaveBeenCalledTimes(2)
  })

  it('consumes a failed attempt window and retries only on later genuine interaction', async () => {
    const send = vi.fn().mockRejectedValue(new Error('offline'))
    const observe = interactionObserver(send, clock)
    observe(realInput, false)
    await vi.advanceTimersByTimeAsync(29_999)
    observe(realInput, false)
    expect(send).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(600_001)
    expect(send).toHaveBeenCalledTimes(1)
    observe(realInput, false)
    await vi.advanceTimersByTimeAsync(0)
    expect(send).toHaveBeenCalledTimes(2)
  })

  it('handles a synchronously throwing sender without retrying automatically', async () => {
    const send = vi.fn(() => { throw new Error('transport unavailable') })
    const observe = interactionObserver(send, clock)
    expect(() => observe(realInput, false)).not.toThrow()
    observe(realInput, false)
    await vi.advanceTimersByTimeAsync(30_000)
    expect(send).toHaveBeenCalledTimes(1)
    observe(realInput, false)
    expect(send).toHaveBeenCalledTimes(2)
  })

  it('ignores synthetic/hidden input without consuming the next eligible window', async () => {
    const send = vi.fn()
    const observe = interactionObserver(send, clock)
    observe({ isTrusted: false }, false)
    observe(realInput, true)
    expect(send).not.toHaveBeenCalled()
    observe(realInput, false)
    await vi.advanceTimersByTimeAsync(30_000)
    observe({ isTrusted: false }, false)
    observe(realInput, true)
    expect(send).toHaveBeenCalledTimes(1)
    observe(realInput, false)
    expect(send).toHaveBeenCalledTimes(2)
  })

  it('aborts on disposal and isolates old settlement from the next user observer', async () => {
    const oldPending = deferred()
    const nextPending = deferred()
    const send = vi.fn<(signal: AbortSignal) => Promise<void>>()
      .mockReturnValueOnce(oldPending.promise).mockReturnValue(nextPending.promise)
    const old = interactionObserver(send, clock)
    old(realInput, false)
    const oldSignal = send.mock.calls[0][0]
    old.dispose()
    expect(oldSignal.aborted).toBe(true)
    old(realInput, false)
    const next = interactionObserver(send, clock)
    next(realInput, false)
    expect(send).toHaveBeenCalledTimes(2)
    expect(send.mock.calls[1][0].aborted).toBe(false)
    oldPending.resolve()
    await vi.advanceTimersByTimeAsync(30_000)
    next(realInput, false)
    expect(send).toHaveBeenCalledTimes(2) // next request is still in flight
    nextPending.resolve()
    await vi.advanceTimersByTimeAsync(0)
    next(realInput, false)
    expect(send).toHaveBeenCalledTimes(3)
    next.dispose()
  })
})
