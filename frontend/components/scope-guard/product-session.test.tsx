// @vitest-environment jsdom
import { StrictMode } from 'react'
import { act, cleanup, render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ProductSession } from './product-session'

const state = vi.hoisted(() => ({ user: { id: 'first' } as { id: string } | null }))
vi.mock('./store', () => ({ useStore: () => state }))

function pendingRequest() {
  let resolve!: (response: Response) => void
  const promise = new Promise<Response>(done => { resolve = done })
  return { promise, resolve: () => resolve(new Response(null, { status: 204 })) }
}

describe('product session observer lifecycle (controlled jsdom input)', () => {
  const spyListeners = () => vi.spyOn(window, 'addEventListener')
  let listeners: ReturnType<typeof spyListeners>
  const fetchMock = vi.fn<typeof fetch>()
  function keyHandlers() {
    return listeners.mock.calls.filter(([type]) => type === 'keydown')
      .map(([, listener]) => listener as (event: Event) => void)
  }
  function interact(handler = keyHandlers().at(-1)!) {
    act(() => handler({ isTrusted: true } as Event))
  }
  beforeEach(() => {
    state.user = { id: 'first' }
    vi.useFakeTimers()
    vi.spyOn(document, 'hidden', 'get').mockReturnValue(false)
    listeners = spyListeners()
    fetchMock.mockReset().mockResolvedValue(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)
  })
  afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals() })

  it('does not reset the request window on a same-user object refresh', async () => {
    const view = render(<ProductSession />)
    expect(fetchMock).not.toHaveBeenCalled()
    interact()
    await act(() => vi.advanceTimersByTimeAsync(0))
    state.user = { id: 'first' }
    view.rerender(<ProductSession />)
    interact()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(keyHandlers()).toHaveLength(1)
    await act(() => vi.advanceTimersByTimeAsync(30_000))
    interact()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('aborts on user change/logout and keeps old settlement separate from the next user', async () => {
    const first = pendingRequest()
    const second = pendingRequest()
    fetchMock.mockReturnValueOnce(first.promise).mockReturnValue(second.promise)
    const removed = vi.spyOn(window, 'removeEventListener')
    const view = render(<ProductSession />)
    const oldHandler = keyHandlers().at(-1)!
    interact(oldHandler)
    const oldSignal = fetchMock.mock.calls[0][1]!.signal!
    state.user = { id: 'second' }
    view.rerender(<ProductSession />)
    expect(oldSignal.aborted).toBe(true)
    interact(oldHandler)
    interact()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    const nextSignal = fetchMock.mock.calls[1][1]!.signal!
    first.resolve()
    await act(() => vi.advanceTimersByTimeAsync(30_000))
    interact()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    state.user = null
    view.rerender(<ProductSession />)
    expect(nextSignal.aborted).toBe(true)
    interact()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(removed.mock.calls.filter(([type]) => type === 'keydown')).toHaveLength(2)
    second.resolve()
    await act(() => vi.advanceTimersByTimeAsync(600_000))
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('disposes on unmount and observes promptly after remount', () => {
    const request = pendingRequest()
    fetchMock.mockReturnValue(request.promise)
    const first = render(<ProductSession />)
    const oldHandler = keyHandlers().at(-1)!
    interact(oldHandler)
    const signal = fetchMock.mock.calls[0][1]!.signal!
    first.unmount()
    expect(signal.aborted).toBe(true)
    render(<ProductSession />)
    interact(oldHandler)
    interact()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('keeps only the active StrictMode effect eligible and creates no mount activity', () => {
    const view = render(<StrictMode><ProductSession /></StrictMode>)
    const handlers = keyHandlers()
    expect(handlers).toHaveLength(2)
    expect(fetchMock).not.toHaveBeenCalled()
    interact(handlers[0])
    expect(fetchMock).not.toHaveBeenCalled()
    interact(handlers[1])
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const signal = fetchMock.mock.calls[0][1]!.signal!
    view.unmount()
    expect(signal.aborted).toBe(true)
    interact(handlers[1])
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})
