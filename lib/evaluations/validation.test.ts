import { describe, expect, it } from 'vitest'
import { ERROR_CODES } from '@/lib/api/errors'
import { parseEvaluationInput, resolveHumanVerdict } from './validation'

const historyEntryId = '11111111-1111-4111-8111-111111111111'
const reasoning = 'The request adds a new deliverable.'

describe('parseEvaluationInput', () => {
  it('accepts correct without humanVerdict', () => {
    const parsed = parseEvaluationInput({
      historyEntryId,
      accuracy: 'correct',
      aiReasoning: reasoning,
    })
    expect(parsed).toEqual({
      ok: true,
      label: {
        historyEntryId,
        accuracy: 'correct',
        aiReasoning: reasoning,
      },
    })
  })

  it('accepts debatable without humanVerdict', () => {
    const parsed = parseEvaluationInput({
      historyEntryId,
      accuracy: 'debatable',
      aiReasoning: `  ${reasoning}  `,
    })
    expect(parsed.ok).toBe(true)
    if (!parsed.ok) return
    expect(parsed.label.accuracy).toBe('debatable')
    expect(parsed.label.aiReasoning).toBe(reasoning)
  })

  it('accepts wrong with a different expected verdict', () => {
    const parsed = parseEvaluationInput({
      historyEntryId,
      accuracy: 'wrong',
      humanVerdict: 'in_scope',
      aiReasoning: reasoning,
    })
    expect(parsed).toEqual({
      ok: true,
      label: {
        historyEntryId,
        accuracy: 'wrong',
        humanVerdict: 'in_scope',
        aiReasoning: reasoning,
      },
    })
  })

  it('rejects correct when humanVerdict is present', () => {
    const parsed = parseEvaluationInput({
      historyEntryId,
      accuracy: 'correct',
      humanVerdict: 'in_scope',
      aiReasoning: reasoning,
    })
    expect(parsed).toEqual({
      ok: false,
      error: ERROR_CODES.evaluationLabelInvalid,
      status: 400,
    })
  })

  it('rejects debatable when humanVerdict is present', () => {
    const parsed = parseEvaluationInput({
      historyEntryId,
      accuracy: 'debatable',
      humanVerdict: 'borderline',
      aiReasoning: reasoning,
    })
    expect(parsed.ok).toBe(false)
    if (parsed.ok) return
    expect(parsed.error).toBe(ERROR_CODES.evaluationLabelInvalid)
    expect(parsed.status).toBe(400)
  })

  it('rejects wrong without humanVerdict', () => {
    const parsed = parseEvaluationInput({
      historyEntryId,
      accuracy: 'wrong',
      aiReasoning: reasoning,
    })
    expect(parsed).toEqual({
      ok: false,
      error: ERROR_CODES.evaluationLabelInvalid,
      status: 400,
    })
  })

  it('rejects wrong when humanVerdict is null', () => {
    const parsed = parseEvaluationInput({
      historyEntryId,
      accuracy: 'wrong',
      humanVerdict: null,
      aiReasoning: reasoning,
    })
    expect(parsed.ok).toBe(false)
    if (parsed.ok) return
    expect(parsed.error).toBe(ERROR_CODES.evaluationLabelInvalid)
  })

  it('rejects invalid accuracy', () => {
    const parsed = parseEvaluationInput({
      historyEntryId,
      accuracy: 'maybe',
      aiReasoning: reasoning,
    })
    expect(parsed).toEqual({
      ok: false,
      error: ERROR_CODES.evaluationLabelInvalid,
      status: 400,
    })
  })

  it('rejects empty reasoning', () => {
    const parsed = parseEvaluationInput({
      historyEntryId,
      accuracy: 'correct',
      aiReasoning: '   ',
    })
    expect(parsed).toEqual({
      ok: false,
      error: ERROR_CODES.evaluationReasoningRequired,
      status: 400,
    })
  })

  it('rejects invalid historyEntryId as not found', () => {
    const parsed = parseEvaluationInput({
      historyEntryId: 'not-a-uuid',
      accuracy: 'correct',
      aiReasoning: reasoning,
    })
    expect(parsed).toEqual({
      ok: false,
      error: ERROR_CODES.evaluationHistoryNotFound,
      status: 404,
    })
  })
})

describe('resolveHumanVerdict', () => {
  it('sets human verdict equal to AI verdict for correct', () => {
    const resolved = resolveHumanVerdict(
      {
        historyEntryId,
        accuracy: 'correct',
        aiReasoning: reasoning,
      },
      'out_of_scope',
    )
    expect(resolved).toEqual({ ok: true, humanVerdict: 'out_of_scope' })
  })

  it('sets human verdict null for debatable', () => {
    const resolved = resolveHumanVerdict(
      {
        historyEntryId,
        accuracy: 'debatable',
        aiReasoning: reasoning,
      },
      'borderline',
    )
    expect(resolved).toEqual({ ok: true, humanVerdict: null })
  })

  it('keeps the expected verdict for wrong when it differs', () => {
    const resolved = resolveHumanVerdict(
      {
        historyEntryId,
        accuracy: 'wrong',
        humanVerdict: 'in_scope',
        aiReasoning: reasoning,
      },
      'out_of_scope',
    )
    expect(resolved).toEqual({ ok: true, humanVerdict: 'in_scope' })
  })

  it('rejects wrong when expected verdict equals the AI verdict', () => {
    const resolved = resolveHumanVerdict(
      {
        historyEntryId,
        accuracy: 'wrong',
        humanVerdict: 'out_of_scope',
        aiReasoning: reasoning,
      },
      'out_of_scope',
    )
    expect(resolved).toEqual({
      ok: false,
      error: ERROR_CODES.evaluationLabelInvalid,
    })
  })
})
