import { describe, expect, it } from 'vitest'
import { buildAnalysisMessages } from '@/lib/llm/prompt'

const base = { scope: 'Build five pages', request: 'Add a blog', industry: 'Development' as const, locale: 'en' as const, startDate: '2026-01-01', draftCreatedAt: '2026-02-01T12:00:00Z', currency: 'USD' as const }

describe('Change Order AI inputs', () => {
  it('supplies hourly rate, currency, duration and explicit end date', () => {
    const [, user] = buildAnalysisMessages({ ...base, pricingModel: 'hourly', hourlyRate: '125.00', endDate: '2026-03-01' })
    expect(user.content).toContain('"hourlyRate":"125.00"')
    expect(user.content).toContain('"currency":"USD"')
    expect(user.content).toContain('"calculationEndDate":"2026-03-01"')
    expect(user.content).toContain('"durationDays":59')
  })
  it('supplies fixed price and draft-date fallback', () => {
    const [, user] = buildAnalysisMessages({ ...base, pricingModel: 'fixed', fixedPrice: '5000.00' })
    expect(user.content).toContain('"fixedPrice":"5000.00"')
    expect(user.content).toContain('"calculationEndDate":"2026-02-01"')
    expect(user.content).toContain('"endDateSource":"draft"')
  })
})
