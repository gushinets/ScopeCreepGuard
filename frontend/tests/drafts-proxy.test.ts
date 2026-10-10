import { describe, expect, it, vi } from 'vitest'
import { NextRequest } from 'next/server'

const verifySessionToken = vi.fn()
vi.mock('@/lib/auth/session', () => ({ SESSION_COOKIE_NAME: 'scg_session', verifySessionToken }))
vi.mock('@/lib/api/forward', () => ({ forwardToBackend: vi.fn() }))
vi.mock('@/lib/api/origin', () => ({ allowsApiOrigin: () => true }))

describe('draft API proxy ownership', () => {
  it('passes all four draft operations to Python without local session parsing', async () => {
    const { proxy } = await import('../proxy')
    for (const [path, method] of [['/api/drafts', 'GET'], ['/api/drafts', 'POST'], ['/api/drafts/id', 'GET'], ['/api/drafts/id', 'PUT']]) {
      const response = await proxy(new NextRequest(`http://app.test${path}`, { method }))
      expect(response.headers.get('x-middleware-next')).toBe('1')
    }
    expect(verifySessionToken).not.toHaveBeenCalled()
  })
})
