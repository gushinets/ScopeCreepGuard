import { expect, it } from 'vitest'
import { withBrowserIdentity } from '@/shared/storage/browser-bootstrap'

it('serializes tab hydration until the first response installs the shared cookie', async () => {
  let queue = Promise.resolve()
  const locks = { request: <T,>(name: string, run: () => Promise<T>): Promise<T> => {
    expect(name).toBe('scg-browser-identity')
    const result = queue.then(run)
    queue = result.then(() => undefined)
    return result
  } }
  let cookie: string | undefined
  let creations = 0
  const load = async () => {
    const received = cookie
    await Promise.resolve()
    if (!received) { creations++; cookie = 'signed-browser' }
    return cookie
  }
  expect(await Promise.all([withBrowserIdentity(load, locks),
    withBrowserIdentity(load, locks)])).toEqual(['signed-browser', 'signed-browser'])
  expect(creations).toBe(1)
})
