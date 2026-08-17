import OpenAI from 'openai'
import type { Locale } from '@/i18n/config'
import type { Industry } from '@/lib/types'
import { ANALYSIS_JSON_SCHEMA } from './analysis-json-schema'
import { buildAnalysisMessages } from './prompt'
import { parseAnalysisResult } from './schema'

export async function analyzeWithOpenAI(input: {
  scope: string
  request: string
  industry: Industry
  locale: Locale
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

  const client = new OpenAI({ apiKey })

  let completion: OpenAI.Chat.Completions.ChatCompletion
  try {
    completion = await client.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: buildAnalysisMessages(input),
      response_format: {
        type: 'json_schema',
        json_schema: {
          name: 'scope_analysis',
          strict: true,
          schema: ANALYSIS_JSON_SCHEMA,
        },
      },
    })
  } catch (error) {
    console.error(
      JSON.stringify({
        event: 'openai_request_failed',
        message: error instanceof Error ? error.message : 'Unknown OpenAI error',
      }),
    )
    throw new Error('openai_request_failed')
  }

  const content = completion.choices[0]?.message?.content
  if (!content) {
    console.error(
      JSON.stringify({
        event: 'openai_empty_content',
        finishReason: completion.choices[0]?.finish_reason ?? null,
      }),
    )
    throw new Error('openai_request_failed')
  }

  let parsed: unknown
  try {
    parsed = JSON.parse(content)
  } catch (error) {
    console.error(
      JSON.stringify({
        event: 'openai_json_parse_failed',
        message: error instanceof Error ? error.message : 'Unknown JSON parse error',
      }),
    )
    throw new Error('openai_request_failed')
  }

  try {
    return parseAnalysisResult(parsed)
  } catch (error) {
    console.error(
      JSON.stringify({
        event: 'openai_analysis_shape_invalid',
        message: error instanceof Error ? error.message : 'invalid_analysis_result',
      }),
    )
    throw new Error('openai_request_failed')
  }
}
