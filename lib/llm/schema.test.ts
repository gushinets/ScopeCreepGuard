import { describe, expect, it } from 'vitest'
import { parseAnalysisResult } from './schema'

const valid = {
  verdict: 'out_of_scope',
  confidence: 88,
  summary: 'Beyond scope.',
  reasoning: 'Adds pages excluded from scope.',
  citations: ['Additional pages beyond the 5 listed'],
  suggestion: 'Send a change order.',
  replies: {
    warm: 'Hi...',
    neutral: 'Hi...',
    firm: 'Hello...',
  },
  changeOrder: {
    description: '3 extra pages',
    timelineImpact: '+1 week',
    additionalCost: '$2400',
    note: 'Draft only.',
  },
}

describe('parseAnalysisResult', () => {
  it('accepts a full valid payload', () => {
    expect(parseAnalysisResult(valid).verdict).toBe('out_of_scope')
  })

  it('accepts missing optional suggestion', () => {
    const { suggestion: _s, ...rest } = valid
    expect(parseAnalysisResult(rest).suggestion).toBeUndefined()
  })

  it('rejects invalid verdict', () => {
    expect(() =>
      parseAnalysisResult({ ...valid, verdict: 'maybe' }),
    ).toThrow('invalid_analysis_result')
  })

  it('rejects non-object', () => {
    expect(() => parseAnalysisResult(null)).toThrow('invalid_analysis_result')
  })

  it('rejects incomplete replies', () => {
    expect(() =>
      parseAnalysisResult({
        ...valid,
        replies: { warm: 'a', neutral: 'b' },
      }),
    ).toThrow('invalid_analysis_result')
  })
})
