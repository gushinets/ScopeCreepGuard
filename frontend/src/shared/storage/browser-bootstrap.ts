type BrowserLocks = { request<T>(name: string, run: () => Promise<T>): Promise<T> }

/** Finish the browser-wide cookie handshake before another tab hydrates. */
export function withBrowserIdentity<T>(load: () => Promise<T>,
  locks: BrowserLocks | undefined = typeof navigator === 'undefined' ? undefined : navigator.locks,
): Promise<T> {
  return locks ? locks.request('scg-browser-identity', load) : load()
}
