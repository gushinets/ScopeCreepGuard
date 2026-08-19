export const ANALYSIS_JSON_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: [
    'verdict',
    'confidence',
    'summary',
    'reasoning',
    'citations',
    'suggestion',
    'replies',
    'changeOrder',
  ],
  properties: {
    verdict: {
      type: 'string',
      enum: ['in_scope', 'borderline', 'out_of_scope'],
    },
    confidence: {
      type: 'integer',
      description:
        'Certainty as a percentage from 0 to 100, not a 0-1 fraction.',
      minimum: 0,
      maximum: 100,
    },
    summary: {
      type: 'string',
      description: 'Non-empty. One-sentence verdict in the output language.',
    },
    reasoning: {
      type: 'string',
      description: 'Non-empty. Explain the verdict from the provided scope only.',
    },
    citations: { type: 'array', items: { type: 'string' } },
    suggestion: { type: 'string' },
    replies: {
      type: 'object',
      additionalProperties: false,
      required: ['warm', 'neutral', 'firm'],
      properties: {
        warm: { type: 'string', description: 'Non-empty client reply.' },
        neutral: { type: 'string', description: 'Non-empty client reply.' },
        firm: { type: 'string', description: 'Non-empty client reply.' },
      },
    },
    changeOrder: {
      type: 'object',
      additionalProperties: false,
      required: ['description', 'timelineImpact', 'additionalCost', 'note'],
      properties: {
        description: {
          type: 'string',
          description:
            'Non-empty in every verdict. For in_scope, name the included work.',
        },
        timelineImpact: {
          type: 'string',
          description:
            'Non-empty in every verdict. For in_scope, say none / no extra time.',
        },
        additionalCost: {
          type: 'string',
          description:
            'Non-empty in every verdict. For in_scope, use included / $0 style text.',
        },
        note: {
          type: 'string',
          description: 'Non-empty draft disclaimer, not legal advice.',
        },
      },
    },
  },
} as const
