import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { useTranslations } from 'use-intl'
import { apiJson } from '@/shared/api/client'

type State = { status: 'not_started' | 'in_progress' | 'completed' | 'skipped'; step: number }
type Event = 'form_opened' | 'project_saved' | 'check_submitted' | 'result_viewed' | 'skip'
const Context = createContext<{ state: State | null; resultStep: number | null; setResultStep: (step: number | null) => void; send: (event: Event) => Promise<void>; skip: () => void }>({ state: null, resultStep: null, setResultStep: () => {}, send: async () => {}, skip: () => {} })
const terminal = (state: State | null) => state?.status === 'completed' || state?.status === 'skipped'

export function OnboardingProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<State | null>(null)
  const [resultStep, setResultStep] = useState<number | null>(null)
  const latest = useRef<State | null>(null)
  const dismissed = useRef(false)
  const pending = useRef<Event[]>([])
  const queue = useRef(Promise.resolve())
  const alive = useRef(true)
  const accept = useCallback((next: State) => {
    if (!alive.current || terminal(latest.current) && !terminal(next) || latest.current && !terminal(next) && next.step < latest.current.step) return
    latest.current = next
    setState(next)
  }, [])
  useEffect(() => {
    alive.current = true
    const refresh = () => { void apiJson<State>('/api/v2/profile/onboarding').then(accept).catch(() => {}) }
    refresh()
    window.addEventListener('focus', refresh)
    return () => { alive.current = false; window.removeEventListener('focus', refresh) }
  }, [accept])
  const send = useCallback((event: Event) => {
    const task = queue.current.then(async () => {
      if (terminal(latest.current) || dismissed.current && event !== 'skip') return
      try {
        pending.current.push(event)
        let next: State | null = null
        while (pending.current.length) {
          next = await apiJson<State>('/api/v2/profile/onboarding', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ event: pending.current[0] }) })
          pending.current.shift()
          accept(next)
          if (terminal(next)) { pending.current = []; break }
        }
        if (!next) return
        accept(next)
      } catch { /* Guidance never blocks project or draft operations. */ }
    })
    queue.current = task
    return task
  }, [accept])
  useEffect(() => {
    const retry = () => {
      const event = pending.current.pop()
      if (event) void send(event)
    }
    window.addEventListener('online', retry)
    window.addEventListener('focus', retry)
    return () => { window.removeEventListener('online', retry); window.removeEventListener('focus', retry) }
  }, [send])
  const skip = () => {
    dismissed.current = true
    setState(null)
    void send('skip')
  }
  return <Context value={{ state: dismissed.current ? null : state, resultStep, setResultStep, send, skip }}>{children}</Context>
}

export const useOnboarding = () => useContext(Context)

export function SkipOnboarding() {
  const { state, skip } = useOnboarding()
  const t = useTranslations()
  if (!state || terminal(state)) return null
  return <button type="button" className="onboarding-skip" onClick={skip}>{t('onboarding.skip')}</button>
}
