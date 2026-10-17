'use client'

import { useEffect } from 'react'
import { interactionObserver } from '@/lib/product-interaction'
import { useStore } from './store'

export function ProductSession() {
  const { user } = useStore()
  const userId = user?.id
  useEffect(() => {
    if (!userId) return
    const observe = interactionObserver(signal => fetch('/api/v2/session/interaction', {
      method: 'POST', credentials: 'same-origin', cache: 'no-store', signal,
    }))
    const listener = (event: Event) => observe(event, document.hidden)
    const events = ['pointerdown', 'keydown', 'input', 'wheel'] as const
    for (const type of events) window.addEventListener(type, listener, { passive: true })
    return () => {
      observe.dispose()
      for (const type of events) window.removeEventListener(type, listener)
    }
  }, [userId])
  return null
}
