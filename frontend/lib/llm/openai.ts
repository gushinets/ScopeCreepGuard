import OpenAI from 'openai'
import type { Locale } from '@/i18n/config'
import { ERROR_CODES, type ErrorCode } from '@/lib/api/errors'
import type { Currency, Industry, PricingModel, Tone } from '@/lib/types'
import { ANALYSIS_JSON_SCHEMA } from './analysis-json-schema'
import { buildAnalysisMessages, buildRegenerationMessages } from './prompt'
import { parseAnalysisResult } from './schema'

const ANALYSIS_JSON_SCHEMA_RECORD = ANALYSIS_JSON_SCHEMA as unknown as {
  [key: string]: unknown
}

export type OpenAIAnalysisResponse = {
  status?:
    | 'completed'
    | 'failed'
    | 'in_progress'
    | 'cancelled'
    | 'queued'
    | 'incomplete'
  output_text: string
  incomplete_details: { reason?: 'max_output_tokens' | 'content_filter' } | null
  usage?: {
    input_tokens: number
    output_tokens: number
    output_tokens_details: { reasoning_tokens: number }
  }
}

export function openaiUsageFields(usage: OpenAIAnalysisResponse['usage']) {
  if (!usage) {
    return {}
  }
  return {
    inputTokens: usage.input_tokens,
    outputTokens: usage.output_tokens,
    reasoningTokens: usage.output_tokens_details.reasoning_tokens,
  }
}

export function openAIErrorDetail(error: unknown): string {
  const parts: string[] = []
  let current: unknown = error
  for (let depth = 0; depth < 4; depth += 1) {
    if (!(current instanceof Error) || current.message.length === 0) break
    parts.push(current.message)
    current = current.cause
  }
  const detail = parts.length > 0 ? parts.join(': ') : 'Unknown OpenAI error'
  return detail.replace(/\/\/[^/\s@]+@/g, '//***@')
}

function proxyConfigured() {
  const httpsProxy = process.env.HTTPS_PROXY
  if (typeof httpsProxy === 'string' && httpsProxy.trim().length > 0) return true
  const httpProxy = process.env.HTTP_PROXY
  return typeof httpProxy === 'string' && httpProxy.trim().length > 0
}

export function analyzeFailureResponse(
  message: string,
): { error: ErrorCode; status: number } {
  if (message === 'openai_api_key_missing') {
    return { error: ERROR_CODES.analysisUnavailable, status: 503 }
  }
  if (
    message === 'openai_json_parse_failed' ||
    message === 'openai_analysis_shape_invalid'
  ) {
    return { error: ERROR_CODES.analysisInvalid, status: 502 }
  }
  return { error: ERROR_CODES.analysisFailed, status: 502 }
}

export function requireCompletedOutputText(
  response: OpenAIAnalysisResponse,
): string {
  if (response.status !== 'completed') {
    console.error(
      JSON.stringify({
        event: 'openai_incomplete',
        status: response.status ?? null,
        incompleteReason: response.incomplete_details?.reason ?? null,
        ...openaiUsageFields(response.usage),
      }),
    )
    throw new Error('openai_request_failed')
  }

  if (response.output_text.trim().length === 0) {
    console.error(
      JSON.stringify({
        event: 'openai_empty_content',
        status: response.status,
        ...openaiUsageFields(response.usage),
      }),
    )
    throw new Error('openai_request_failed')
  }

  return response.output_text
}

function parseOpenAIAnalysisResponse(response: OpenAIAnalysisResponse, locale: Locale, override?: string) {
  const content = requireCompletedOutputText(response)

  let parsed: unknown
  try {
    parsed = JSON.parse(content)
  } catch {
    console.error(
      JSON.stringify({
        event: 'openai_json_parse_failed',
        ...openaiUsageFields(response.usage),
      }),
    )
    throw new Error('openai_json_parse_failed')
  }

  try {
    return parseAnalysisResult(parsed, locale, override)
  } catch (error) {
    const keys =
      parsed && typeof parsed === 'object' && !Array.isArray(parsed)
        ? Object.keys(parsed)
        : []
    console.error(
      JSON.stringify({
        event: 'openai_analysis_shape_invalid',
        reason: error instanceof Error ? error.message : 'unknown',
        keys,
        ...openaiUsageFields(response.usage),
      }),
    )
    if (
      error instanceof Error &&
      error.message.startsWith('invalid_analysis_result')
    ) {
      throw new Error('openai_analysis_shape_invalid')
    }
    throw error
  }
}

export async function analyzeWithOpenAI(input: {
  scope: string
  request: string
  industry: Industry
  locale: Locale
  pricingModel?: PricingModel | null
  currency?: Currency | null
  hourlyRate?: string | null
  fixedPrice?: string | null
  startDate?: string | null
  endDate?: string
  draftCreatedAt?: string
  documentLanguage?: string
}) {
  const apiKey = process.env.OPENAI_API_KEY
  if (!apiKey || apiKey.trim().length === 0) {
    console.error(
      JSON.stringify({
        event: 'openai_api_key_missing',
      }),
    )
    throw new Error('openai_api_key_missing')
  }

  const client = new OpenAI({ apiKey, maxRetries: 2 })
  const [system, user] = buildAnalysisMessages(input)

  let response: OpenAI.Responses.Response
  try {
    response = await client.responses.create({
      model: 'gpt-5.4-nano',
      reasoning: { effort: 'medium' },
      instructions: system.content,
      input: user.content,
      text: {
        format: {
          type: 'json_schema',
          name: 'scope_analysis',
          strict: true,
          schema: ANALYSIS_JSON_SCHEMA_RECORD,
        },
      },
    })
  } catch (error) {
    console.error(
      JSON.stringify({
        event: 'openai_request_failed',
        proxyConfigured: proxyConfigured(),
        message: openAIErrorDetail(error),
      }),
    )
    throw new Error('openai_request_failed')
  }

  return parseOpenAIAnalysisResponse(response, input.locale, input.documentLanguage)
}

export async function regenerateReplyWithOpenAI(input: {
  scope: string
  request: string
  industry: Industry
  locale: Locale
  tone: Tone
  previousReply: string
  documentLanguage?: string
}) {
  const apiKey = process.env.OPENAI_API_KEY
  if (!apiKey || apiKey.trim().length === 0) {
    console.error(
      JSON.stringify({
        event: 'openai_api_key_missing',
      }),
    )
    throw new Error('openai_api_key_missing')
  }

  const client = new OpenAI({ apiKey, maxRetries: 2 })
  const [system, user] = buildRegenerationMessages(input)

  let response: OpenAI.Responses.Response
  try {
    response = await client.responses.create({
      model: 'gpt-5.4-nano',
      reasoning: { effort: 'high' },
      instructions: system.content,
      input: user.content,
      text: {
        format: {
          type: 'json_schema',
          name: 'scope_analysis',
          strict: true,
          schema: ANALYSIS_JSON_SCHEMA_RECORD,
        },
      },
    })
  } catch (error) {
    console.error(
      JSON.stringify({
        event: 'openai_regeneration_request_failed',
        proxyConfigured: proxyConfigured(),
        message: openAIErrorDetail(error),
      }),
    )
    throw new Error('openai_request_failed')
  }

  const result = parseOpenAIAnalysisResponse(response, input.locale, input.documentLanguage)
  return result.replies[input.tone]
}
