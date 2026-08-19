import { describe, expect, it } from 'vitest'
import {
  openaiUsageFields,
  requireCompletedOutputText,
  type OpenAIAnalysisResponse,
} from './openai'

const completed: OpenAIAnalysisResponse = {
  status: 'completed',
  output_text: '{"verdict":"in_scope"}',
  incomplete_details: null,
  usage: {
    input_tokens: 100,
    output_tokens: 40,
    output_tokens_details: { reasoning_tokens: 12 },
  },
}

describe('openaiUsageFields', () => {
  it('returns input, output, and reasoning token counts when usage is present', () => {
    expect(openaiUsageFields(completed.usage)).toEqual({
      inputTokens: 100,
      outputTokens: 40,
      reasoningTokens: 12,
    })
  })

  it('returns an empty object when usage is missing', () => {
    expect(openaiUsageFields(undefined)).toEqual({})
  })
})

describe('requireCompletedOutputText', () => {
  it('returns output_text when status is completed', () => {
    expect(requireCompletedOutputText(completed)).toBe(
      '{"verdict":"in_scope"}',
    )
  })

  it('throws when status is not completed', () => {
    expect(() =>
      requireCompletedOutputText({
        ...completed,
        status: 'incomplete',
        incomplete_details: { reason: 'max_output_tokens' },
      }),
    ).toThrow('openai_request_failed')
  })

  it('throws when status is omitted', () => {
    const { status: _status, ...rest } = completed
    expect(() =>
      requireCompletedOutputText(rest as OpenAIAnalysisResponse),
    ).toThrow('openai_request_failed')
  })

  it('throws when output_text is empty or whitespace', () => {
    expect(() =>
      requireCompletedOutputText({ ...completed, output_text: '' }),
    ).toThrow('openai_request_failed')
    expect(() =>
      requireCompletedOutputText({ ...completed, output_text: '   ' }),
    ).toThrow('openai_request_failed')
  })
})
