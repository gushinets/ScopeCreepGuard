import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ERROR_CODES } from '@/lib/api/errors'
import { ANALYSIS_JSON_SCHEMA } from './analysis-json-schema'
import { buildAnalysisMessages, buildRegenerationMessages } from './prompt'

const { createMock, openAIConstructorMock } = vi.hoisted(() => ({
  createMock: vi.fn(),
  openAIConstructorMock: vi.fn(),
}))

vi.mock('openai', () => ({
  default: class MockOpenAI {
    responses = { create: createMock }

    constructor(options: unknown) {
      openAIConstructorMock(options)
    }
  },
}))

import {
  analyzeFailureResponse,
  analyzeWithOpenAI,
  openAIErrorDetail,
  openaiUsageFields,
  regenerateReplyWithOpenAI,
  requireCompletedOutputText,
  type OpenAIAnalysisResponse,
} from './openai'

const originalApiKey = process.env.OPENAI_API_KEY

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

const validResult = {
  verdict: 'out_of_scope',
  confidence: 88,
  summary: 'Beyond scope.',
  reasoning: 'Adds pages excluded from scope.',
  citations: ['Additional pages beyond the 5 listed'],
  suggestion: 'Send a change order.',
  replies: { warm: 'Hi...', neutral: 'Hi...', firm: 'Hello...' },
  changeOrder: {
    description: '3 extra pages',
    timelineImpact: '+1 week',
    additionalCost: '$2400',
    note: 'Draft only.',
  },
}

const analysisInput = {
  scope: 'Five website pages.',
  request: 'Please add three pages.',
  industry: 'Development' as const,
  locale: 'en' as const,
}

beforeEach(() => {
  process.env.OPENAI_API_KEY = 'test-api-key'
  createMock.mockReset()
  openAIConstructorMock.mockReset()
})

afterEach(() => {
  if (originalApiKey === undefined) {
    delete process.env.OPENAI_API_KEY
  } else {
    process.env.OPENAI_API_KEY = originalApiKey
  }
})

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

describe('ANALYSIS_JSON_SCHEMA', () => {
  it('requires confidence as an integer percent 0-100', () => {
    expect(ANALYSIS_JSON_SCHEMA.properties.confidence.type).toBe('integer')
    expect(ANALYSIS_JSON_SCHEMA.properties.confidence.minimum).toBe(0)
    expect(ANALYSIS_JSON_SCHEMA.properties.confidence.maximum).toBe(100)
  })
})

describe('analyzeWithOpenAI', () => {
  it('sends the required Responses API request and returns a valid analysis', async () => {
    createMock.mockResolvedValue({
      status: 'completed',
      output_text: JSON.stringify(validResult),
      incomplete_details: null,
    })
    const [system, user] = buildAnalysisMessages(analysisInput)

    await expect(analyzeWithOpenAI(analysisInput)).resolves.toEqual({ ...validResult, clientLanguage: 'en' })
    expect(openAIConstructorMock).toHaveBeenCalledWith({
      apiKey: 'test-api-key',
      maxRetries: 2,
    })
    expect(createMock).toHaveBeenCalledOnce()
    expect(createMock).toHaveBeenCalledWith({
      model: 'gpt-5.4-nano',
      reasoning: { effort: 'medium' },
      instructions: system.content,
      input: user.content,
      text: {
        format: {
          type: 'json_schema',
          name: 'scope_analysis',
          strict: true,
          schema: ANALYSIS_JSON_SCHEMA,
        },
      },
    })
  })

  it('throws a stable code when the model output is invalid JSON', async () => {
    createMock.mockResolvedValue({
      status: 'completed',
      output_text: '{invalid',
      incomplete_details: null,
    })

    await expect(analyzeWithOpenAI(analysisInput)).rejects.toThrow(
      'openai_json_parse_failed',
    )
  })

  it('throws a stable code when parsed model output has an invalid shape', async () => {
    createMock.mockResolvedValue({
      status: 'completed',
      output_text: JSON.stringify({ ...validResult, verdict: 'invalid' }),
      incomplete_details: null,
    })

    await expect(analyzeWithOpenAI(analysisInput)).rejects.toThrow(
      'openai_analysis_shape_invalid',
    )
  })

  it('rejects non-integer confidence in otherwise valid model output', async () => {
    createMock.mockResolvedValue({
      status: 'completed',
      output_text: JSON.stringify({ ...validResult, confidence: 0.5 }),
      incomplete_details: null,
    })

    await expect(analyzeWithOpenAI(analysisInput)).rejects.toThrow(
      'openai_analysis_shape_invalid',
    )
  })

  it('rejects a missing API key before creating a request', async () => {
    delete process.env.OPENAI_API_KEY

    await expect(analyzeWithOpenAI(analysisInput)).rejects.toThrow(
      'openai_api_key_missing',
    )
    expect(createMock).not.toHaveBeenCalled()
  })
})

describe('regenerateReplyWithOpenAI', () => {
  it('uses high reasoning, parses the full result, and returns the selected tone', async () => {
    createMock.mockResolvedValue({
      status: 'completed',
      output_text: JSON.stringify(validResult),
      incomplete_details: null,
    })
    const input = {
      ...analysisInput,
      tone: 'firm' as const,
      previousReply: 'A previous firm reply.',
    }
    const [system, user] = buildRegenerationMessages(input)

    await expect(regenerateReplyWithOpenAI(input)).resolves.toBe(
      validResult.replies.firm,
    )
    expect(createMock).toHaveBeenCalledWith({
      model: 'gpt-5.4-nano',
      reasoning: { effort: 'high' },
      instructions: system.content,
      input: user.content,
      text: {
        format: {
          type: 'json_schema',
          name: 'scope_analysis',
          strict: true,
          schema: ANALYSIS_JSON_SCHEMA,
        },
      },
    })
    expect(createMock.mock.calls[0]?.[0]).not.toHaveProperty('temperature')
    expect(createMock.mock.calls[0]?.[0]).not.toHaveProperty('previous_response_id')
  })
})


describe('openAIErrorDetail', () => {
  it('includes the connection cause and redacts proxy credentials', () => {
    const cause = new Error(
      'Connect Timeout Error (attempted address: 10.0.0.8:443, timeout: 10000ms)',
    )
    const error = new Error('Connection error.', { cause })
    expect(
      openAIErrorDetail(
        new Error('fetch failed: http://user:secret@proxy.internal:8888', { cause: error }),
      ),
    ).toBe(
      'fetch failed: http://***@proxy.internal:8888: Connection error.: Connect Timeout Error (attempted address: 10.0.0.8:443, timeout: 10000ms)',
    )
  })
})

describe('analyzeFailureResponse', () => {
  it.each([
    [
      'openai_api_key_missing',
      { error: ERROR_CODES.analysisUnavailable, status: 503 },
    ],
    [
      'openai_json_parse_failed',
      { error: ERROR_CODES.analysisInvalid, status: 502 },
    ],
    [
      'openai_analysis_shape_invalid',
      { error: ERROR_CODES.analysisInvalid, status: 502 },
    ],
    [
      'openai_request_failed',
      { error: ERROR_CODES.analysisFailed, status: 502 },
    ],
  ])('maps %s to its API error response', (message, expected) => {
    expect(analyzeFailureResponse(message)).toEqual(expected)
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
