import { expect, it } from 'vitest'
import en from '@/shared/i18n/messages/en.json'
import ru from '@/shared/i18n/messages/ru.json'

it('keeps provider configuration out of the analysis error shown to users', () => {
  for (const message of [en.errors.analysisUnavailable, ru.errors.analysisUnavailable]) {
    expect(message).not.toMatch(/openai|api[_ ]?key/i)
  }
})
