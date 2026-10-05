import { describe, expect, it } from 'vitest'
import { parseProjectInput } from './validation'

const valid = {
  name: 'Website', scope: 'Build a website', industry: 'Design',
  startDate: '2026-10-01', pricingModel: 'hourly', currency: 'USD', hourlyRate: '125.00',
}

describe('project commercial validation', () => {
  it.each(['name', 'scope', 'startDate', 'pricingModel', 'currency', 'hourlyRate'])('rejects missing %s', (field) => {
    expect(parseProjectInput({ ...valid, [field]: '' }).ok).toBe(false)
  })

  it('rejects impossible dates and nonpositive prices', () => {
    expect(parseProjectInput({ ...valid, startDate: '2026-02-30' }).ok).toBe(false)
    expect(parseProjectInput({ ...valid, hourlyRate: '0' }).ok).toBe(false)
  })

  it('requires fixed project price only for fixed pricing', () => {
    expect(parseProjectInput({ ...valid, pricingModel: 'fixed', hourlyRate: '', fixedPrice: '3000' })).toMatchObject({ ok: true, project: { fixedPrice: '3000.00', hourlyRate: null } })
    expect(parseProjectInput({ ...valid, pricingModel: 'fixed', hourlyRate: '', fixedPrice: '' }).ok).toBe(false)
  })

  it('never returns optional browser details in the persistence payload', () => {
    const result = parseProjectInput({ ...valid, clientName: 'Acme', clientEmail: 'x@y.test', endDate: '2026-12-01', client: 'Old field' })
    expect(result.ok).toBe(true)
    if (result.ok) expect(result.project).not.toHaveProperty('client')
    if (result.ok) expect(result.project).not.toHaveProperty('endDate')
  })
})
