import { describe, expect, it } from 'vitest'
import { ERROR_CODES } from '@/lib/api/errors'
import { ANALYSIS_INPUT_MAX_CHARS } from './analyze-request'
import { parseRegenerateReplyBody } from './regenerate-request'

const validBody = {
  projectId: 'project-1',
  request: 'Please add a blog.',
  tone: 'neutral',
  previousReply: 'That work is outside the agreed scope.',
}

describe('parseRegenerateReplyBody', () => {
  it.each([
    [{ ...validBody, projectId: '' }, ERROR_CODES.requestBodyInvalid],
    [{ ...validBody, request: '   ' }, ERROR_CODES.requestRequired],
    [{ ...validBody, tone: 'casual' }, ERROR_CODES.requestBodyInvalid],
    [{ ...validBody, previousReply: '' }, ERROR_CODES.requestBodyInvalid],
    [{ ...validBody, previousReply: 42 }, ERROR_CODES.requestBodyInvalid],
  ])('rejects an invalid request body', (body, error) => {
    expect(parseRegenerateReplyBody(body)).toEqual({ ok: false, error })
  })

  it.each(['request', 'previousReply'] as const)(
    'rejects an oversized %s',
    (field) => {
      expect(
        parseRegenerateReplyBody({
          ...validBody,
          [field]: 'x'.repeat(ANALYSIS_INPUT_MAX_CHARS + 1),
        }),
      ).toEqual({ ok: false, error: ERROR_CODES.analysisInputTooLarge })
    },
  )

  it('trims and returns a valid request', () => {
    expect(
      parseRegenerateReplyBody({
        projectId: ' project-1 ',
        request: ' Request text ',
        tone: 'firm',
        previousReply: ' Previous reply ',
      }),
    ).toEqual({
      ok: true,
      value: {
        projectId: 'project-1',
        request: 'Request text',
        tone: 'firm',
        previousReply: 'Previous reply',
      },
    })
  })
})
