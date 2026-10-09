import { describe, expect, it } from 'vitest'
import { projectTiming } from './estimate-context'

describe('project timing', () => {
  it('uses a provided project end date instead of draft creation date', () => {
    expect(projectTiming('2026-01-01', '2026-03-01', '2026-02-01')).toMatchObject({ calculationEndDate: '2026-03-01', durationDays: 59, endDateSource: 'explicit' })
  })
  it('falls back to the date the draft is created', () => {
    expect(projectTiming('2026-01-01', undefined, '2026-02-01')).toMatchObject({ calculationEndDate: '2026-02-01', durationDays: 31, endDateSource: 'draft' })
  })
  it('uses calendar days around daylight-saving transitions', () => {
    expect(projectTiming('2026-03-28', '2026-03-30', '2026-03-29').durationDays).toBe(2)
  })
})
