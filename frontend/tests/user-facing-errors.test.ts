import { expect, it } from 'vitest'
import en from '@/messages/en.json'
import ru from '@/messages/ru.json'

it('keeps provider configuration out of the analysis error shown to users', () => {
  for (const message of [en.errors.analysisUnavailable, ru.errors.analysisUnavailable]) {
    expect(message).not.toMatch(/openai|api[_ ]?key/i)
  }
})
