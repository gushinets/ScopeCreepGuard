import { beforeEach, describe, expect, it, vi } from 'vitest'
import { readChangeOrder } from './draft-storage'

describe('Change Order draft storage', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(), setItem: vi.fn(), removeItem: vi.fn(), clear: vi.fn(), key: vi.fn(), length: 0,
    })
  })

  it('normalizes a valid legacy draft without discarding its values', () => {
    vi.mocked(localStorage.getItem).mockReturnValue(JSON.stringify({
      createdAt: '2026-10-05T12:00:00Z', language: 'en', projectName: 'Website',
      description: 'Add a blog', estimatedHours: '8', additionalCost: '800', currency: 'USD',
      approvedBy: 'Ana Ruiz',
    }))

    expect(readChangeOrder('u1', 'p1', 'h1')).toMatchObject({
      projectName: 'Website', description: 'Add a blog', estimatedHours: '8', additionalCost: '800',
      providerName: '', clientApproverName: 'Ana Ruiz', approvalDate: '', noAdditionalCharge: false,
      timelineImpact: '', rationale: '', note: '', clientName: '', clientEmail: '', endDate: '', additionalTerms: '',
    })
  })
})
