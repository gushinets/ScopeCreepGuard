import { describe, expect, it } from 'vitest'
import { allowAnalyze } from './rate-limit'

const WINDOW_MS = 60_000

describe('allowAnalyze', () => {
  it('allows up to 10 requests per user within 60 seconds', () => {
    const userId = 'user-rate-limit-10'
    const start = 1_000_000

    for (let i = 0; i < 10; i++) {
      expect(allowAnalyze(userId, start + i)).toBe(true)
    }
    expect(allowAnalyze(userId, start + 10)).toBe(false)
  })

  it('allows a new request after the window expires', () => {
    const userId = 'user-rate-limit-window'
    const start = 2_000_000

    for (let i = 0; i < 10; i++) {
      expect(allowAnalyze(userId, start + i)).toBe(true)
    }
    expect(allowAnalyze(userId, start + 10)).toBe(false)
    expect(allowAnalyze(userId, start + WINDOW_MS + 1)).toBe(true)
  })
})
