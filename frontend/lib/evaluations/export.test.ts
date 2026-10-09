import { describe, expect, it } from 'vitest'
import { serializeEvaluationJsonl, toEvaluationJsonlRecord } from './export'

const baseRow = {
  scope: 'Build a 5-page marketing site.',
  request: 'Add 3 extra pages.',
  aiVerdict: 'out_of_scope' as const,
  humanVerdict: 'in_scope' as const,
  aiReasoning: 'Extra pages exceed the page limit.',
  industry: 'Development' as const,
}

describe('toEvaluationJsonlRecord', () => {
  it('maps DB verdicts and industry into the JSONL contract', () => {
    const record = toEvaluationJsonlRecord(baseRow)
    expect(record).toEqual({
      scope: 'Build a 5-page marketing site.',
      request: 'Add 3 extra pages.',
      ai_verdict: 'OUT_OF_SCOPE',
      human_verdict: 'IN_SCOPE',
      ai_reasoning: 'Extra pages exceed the page limit.',
      project_type: 'development',
    })
    expect(Object.keys(record)).toEqual([
      'scope',
      'request',
      'ai_verdict',
      'human_verdict',
      'ai_reasoning',
      'project_type',
    ])
    expect(record).not.toHaveProperty('accuracy')
  })

  it('emits null human_verdict for a debatable row', () => {
    const record = toEvaluationJsonlRecord({
      ...baseRow,
      aiVerdict: 'borderline',
      humanVerdict: null,
      industry: 'Design',
    })
    expect(record.ai_verdict).toBe('BORDERLINE')
    expect(record.human_verdict).toBeNull()
    expect(record.project_type).toBe('design')
  })

  it('maps Marketing to marketing', () => {
    const record = toEvaluationJsonlRecord({
      ...baseRow,
      industry: 'Marketing',
      aiVerdict: 'in_scope',
      humanVerdict: 'in_scope',
    })
    expect(record.ai_verdict).toBe('IN_SCOPE')
    expect(record.project_type).toBe('marketing')
  })
})

describe('serializeEvaluationJsonl', () => {
  it('returns an empty string for zero rows', () => {
    expect(serializeEvaluationJsonl([])).toBe('')
  })

  it('writes two compact objects with a trailing newline', () => {
    const first = toEvaluationJsonlRecord({
      ...baseRow,
      humanVerdict: null,
    })
    const second = toEvaluationJsonlRecord({
      ...baseRow,
      request: 'Add a blog section.',
      aiVerdict: 'in_scope',
      humanVerdict: 'in_scope',
      industry: 'Marketing',
    })
    const body = serializeEvaluationJsonl([first, second])
    const lines = body.split('\n')
    expect(lines).toHaveLength(3)
    expect(lines[2]).toBe('')
    expect(JSON.parse(lines[0]!).request).toBe('Add 3 extra pages.')
    expect(JSON.parse(lines[1]!).request).toBe('Add a blog section.')
  })

  it('writes one compact object per line with a trailing newline', () => {
    const record = toEvaluationJsonlRecord({
      ...baseRow,
      humanVerdict: null,
    })
    const body = serializeEvaluationJsonl([record])
    expect(body).toBe(
      '{"scope":"Build a 5-page marketing site.","request":"Add 3 extra pages.","ai_verdict":"OUT_OF_SCOPE","human_verdict":null,"ai_reasoning":"Extra pages exceed the page limit.","project_type":"development"}\n',
    )
    const parsed = JSON.parse(body.trimEnd()) as Record<string, unknown>
    expect(Object.keys(parsed)).toEqual([
      'scope',
      'request',
      'ai_verdict',
      'human_verdict',
      'ai_reasoning',
      'project_type',
    ])
  })
})
