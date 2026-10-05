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

  it('accepts integer confidence 0-100', () => {
    expect(parseAnalysisResult({ ...valid, confidence: 88 }).confidence).toBe(88)
  })

  it('rejects non-integer confidence', () => {
    expect(() => parseAnalysisResult({ ...valid, confidence: 87.6 })).toThrow(
      'invalid_analysis_result:confidence',
    )
    expect(() => parseAnalysisResult({ ...valid, confidence: 0.5 })).toThrow(
      'invalid_analysis_result:confidence',
    )
    expect(() => parseAnalysisResult({ ...valid, confidence: 0.95 })).toThrow(
      'invalid_analysis_result:confidence',
    )
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

  it('preserves the scope verdict when a proposed estimate is zero', () => {
    const parsed = parseAnalysisResult({ ...valid, hasAdditionalWork: true, changeOrder: { ...valid.changeOrder, estimatedHours: 0, additionalCost: '0', currency: 'USD', rationale: 'Extra work.' } })
    expect(parsed.verdict).toBe('out_of_scope')
    expect(parsed.estimateValid).toBe(false)
  })

  it('rejects empty changeOrder fields with a field-specific error', () => {
    expect(() =>
      parseAnalysisResult({
        ...valid,
        changeOrder: { ...valid.changeOrder, description: '' },
      }),
    ).toThrow('invalid_analysis_result:changeOrder.description')
    expect(() =>
      parseAnalysisResult({
        ...valid,
        changeOrder: { ...valid.changeOrder, timelineImpact: '   ' },
      }),
    ).toThrow('invalid_analysis_result:changeOrder.timelineImpact')
  })
})
