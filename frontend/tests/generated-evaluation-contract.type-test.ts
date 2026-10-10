import type { operations } from '@/lib/api/generated'

type EvaluationRequest = operations['create_evaluation_api_evaluations_post']['requestBody']['content']['application/json']

const historyEntryId = '11111111-1111-4111-8111-111111111111'

const correct: EvaluationRequest = {
  historyEntryId,
  accuracy: 'correct',
  aiReasoning: 'The AI verdict matches.',
}
const debatable: EvaluationRequest = {
  historyEntryId,
  accuracy: 'debatable',
  aiReasoning: 'The boundary is subjective.',
}
const wrong: EvaluationRequest = {
  historyEntryId,
  accuracy: 'wrong',
  aiReasoning: 'The request is inside the agreed scope.',
  humanVerdict: 'in_scope',
}

// @ts-expect-error wrong evaluations require a human verdict.
const wrongWithoutHumanVerdict: EvaluationRequest = {
  historyEntryId,
  accuracy: 'wrong',
  aiReasoning: 'The request is inside the agreed scope.',
}

const correctWithHumanVerdict: EvaluationRequest = {
  historyEntryId,
  accuracy: 'correct',
  aiReasoning: 'The AI verdict matches.',
  // @ts-expect-error correct evaluations forbid a human verdict.
  humanVerdict: 'in_scope',
}

const debatableWithHumanVerdict: EvaluationRequest = {
  historyEntryId,
  accuracy: 'debatable',
  aiReasoning: 'The boundary is subjective.',
  // @ts-expect-error debatable evaluations forbid a human verdict.
  humanVerdict: 'borderline',
}

void [
  correct,
  debatable,
  wrong,
  wrongWithoutHumanVerdict,
  correctWithHumanVerdict,
  debatableWithHumanVerdict,
]
