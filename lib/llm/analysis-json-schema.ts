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
      type: 'number',
      description:
        'Certainty as a percentage from 0 to 100, not a 0-1 fraction.',
      minimum: 0,
      maximum: 100,
    },
    summary: { type: 'string' },
    reasoning: { type: 'string' },
    citations: { type: 'array', items: { type: 'string' } },
    suggestion: { type: 'string' },
    replies: {
      type: 'object',
      additionalProperties: false,
      required: ['warm', 'neutral', 'firm'],
      properties: {
        warm: { type: 'string' },
        neutral: { type: 'string' },
        firm: { type: 'string' },
      },
    },
    changeOrder: {
      type: 'object',
      additionalProperties: false,
      required: ['description', 'timelineImpact', 'additionalCost', 'note'],
      properties: {
        description: { type: 'string' },
        timelineImpact: { type: 'string' },
        additionalCost: { type: 'string' },
        note: { type: 'string' },
      },
    },
  },
} as const
