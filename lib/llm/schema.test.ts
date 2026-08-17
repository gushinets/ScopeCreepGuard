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

  it('omits empty string suggestion', () => {
    expect(parseAnalysisResult({ ...valid, suggestion: '' }).suggestion).toBeUndefined()
  })

  it('rejects invalid verdict', () => {
    expect(() =>
      parseAnalysisResult({ ...valid, verdict: 'maybe' }),
    ).toThrow('invalid_analysis_result')
  })

  it('accepts confidence at 0 and 100', () => {
    expect(parseAnalysisResult({ ...valid, confidence: 0 }).confidence).toBe(0)
    expect(parseAnalysisResult({ ...valid, confidence: 100 }).confidence).toBe(100)
  })

  it('keeps percent-scale confidence as an integer 0-100', () => {
    expect(parseAnalysisResult({ ...valid, confidence: 88 }).confidence).toBe(88)
    expect(parseAnalysisResult({ ...valid, confidence: 87.6 }).confidence).toBe(88)
  })

  it('converts 0-1 fraction confidence into a percent', () => {
    expect(parseAnalysisResult({ ...valid, confidence: 0.95 }).confidence).toBe(95)
    expect(parseAnalysisResult({ ...valid, confidence: 0.5 }).confidence).toBe(50)
  })

  it('rejects out-of-range confidence', () => {
    expect(() => parseAnalysisResult({ ...valid, confidence: -5 })).toThrow(
      'invalid_analysis_result',
    )
    expect(() => parseAnalysisResult({ ...valid, confidence: 500 })).toThrow(
      'invalid_analysis_result',
    )
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
