import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { apiJson, ApiClientError } from '@/shared/api/client'
import { ERROR_CODES, type ErrorCode } from '@/shared/api/errors'
import { featureContext } from '@/shared/ui/feature-context'
import { withBrowserIdentity } from '@/shared/storage/browser-bootstrap'

export interface AuthUser { id: string; email: string }
type SessionState = { user: AuthUser | null; loading: boolean; error: ErrorCode | ''; refresh: () => Promise<AuthUser | null>; authenticated: (user: AuthUser) => void; logout: () => Promise<void> }
export const [SessionContext, useSession] = featureContext<SessionState>('Session')

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ErrorCode | ''>('')
  const pending = useRef<Promise<AuthUser | null> | null>(null)
  const generation = useRef(0)
  const refresh = useCallback(() => {
    if (pending.current) return pending.current
    const run = generation.current
    const task = withBrowserIdentity(async () => {
      try {
        const { user: identity } = await apiJson<{ user: AuthUser }>('/api/auth/me', { cache: 'no-store' })
        if (run === generation.current) { setUser(identity); setError('') }
        return identity
      } catch (failure) {
        if (run !== generation.current) return null
        if (failure instanceof ApiClientError && failure.status === 401) { setUser(null); setError(''); return null }
        setError(ERROR_CODES.authServiceUnavailable)
        throw failure
      } finally { if (run === generation.current) setLoading(false) }
    })
    pending.current = task
    void task.finally(() => { if (pending.current === task) pending.current = null }).catch(() => {})
    return task
  }, [])
  useEffect(() => { void refresh().catch(() => {}) }, [refresh])
  useEffect(() => {
    const focus = () => { void refresh().catch(() => {}) }
    const expired = () => { generation.current++; pending.current = null; setUser(null); setError(''); setLoading(false) }
    window.addEventListener('focus', focus)
    window.addEventListener('scg:session-expired', expired)
    return () => { window.removeEventListener('focus', focus); window.removeEventListener('scg:session-expired', expired) }
  }, [refresh])
  const authenticated = (identity: AuthUser) => { generation.current++; pending.current = null; setUser(identity); setError(''); setLoading(false) }
  async function logout() {
    await apiJson('/api/auth/logout', { method: 'POST' })
    generation.current++; pending.current = null; setUser(null); setError(''); setLoading(false)
  }
  return <SessionContext.Provider value={{ user, loading, error, refresh, authenticated, logout }}>{children}</SessionContext.Provider>
}
