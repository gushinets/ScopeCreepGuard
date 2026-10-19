import { describe, expect, it } from 'vitest'
import en from '@/shared/i18n/messages/en.json'
import ru from '@/shared/i18n/messages/ru.json'

describe('Change Order localization', () => {
  it('has matching Russian and English keys for new controls and errors', () => {
    for (const group of ['changeOrder', 'projects', 'result', 'errors'] as const) {
      expect(Object.keys(ru[group]).sort()).toEqual(Object.keys(en[group]).sort())
    }
    expect(ru.changeOrder.draft).not.toBe(en.changeOrder.draft)
    expect(ru.projects.required).not.toBe(en.projects.required)
  })
})
