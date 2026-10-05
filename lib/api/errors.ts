export const ERROR_CODES = {
  requestBodyInvalid: 'errors.requestBodyInvalid',
  emailRequired: 'errors.emailRequired',
  passwordRequired: 'errors.passwordRequired',
  invalidEmail: 'errors.invalidEmail',
  passwordTooShort: 'errors.passwordTooShort',
  duplicateEmail: 'errors.duplicateEmail',
  invalidCredentials: 'errors.invalidCredentials',
  authRequired: 'errors.authRequired',
  projectNotFound: 'errors.projectNotFound',
  projectNameRequired: 'errors.projectNameRequired',
  scopeRequired: 'errors.scopeRequired',
  industryInvalid: 'errors.industryInvalid',
  clientInvalid: 'errors.clientInvalid',
  startDateInvalid: 'errors.startDateInvalid',
  pricingModelInvalid: 'errors.pricingModelInvalid',
  currencyInvalid: 'errors.currencyInvalid',
  hourlyRateInvalid: 'errors.hourlyRateInvalid',
  fixedPriceInvalid: 'errors.fixedPriceInvalid',
  historyDateInvalid: 'errors.historyDateInvalid',
  requestRequired: 'errors.requestRequired',
  verdictInvalid: 'errors.verdictInvalid',
  summaryRequired: 'errors.summaryRequired',
  localeInvalid: 'errors.localeInvalid',
  requestFailed: 'errors.requestFailed',
  authServiceUnavailable: 'errors.authServiceUnavailable',
  workspaceLoadFailed: 'errors.workspaceLoadFailed',
  saveProjectFailed: 'errors.saveProjectFailed',
  analysisUnavailable: 'errors.analysisUnavailable',
  analysisFailed: 'errors.analysisFailed',
  analysisInvalid: 'errors.analysisInvalid',
  analysisInputTooLarge: 'errors.analysisInputTooLarge',
  analysisRateLimited: 'errors.analysisRateLimited',
  scopeFileTooLarge: 'errors.scopeFileTooLarge',
  scopeFileUnsupported: 'errors.scopeFileUnsupported',
  scopeFileEmpty: 'errors.scopeFileEmpty',
  evaluationReasoningRequired: 'errors.evaluationReasoningRequired',
  evaluationLabelInvalid: 'errors.evaluationLabelInvalid',
  evaluationHistoryNotFound: 'errors.evaluationHistoryNotFound',
} as const

export type ErrorCode = (typeof ERROR_CODES)[keyof typeof ERROR_CODES]

const errorCodeValues = new Set<string>(Object.values(ERROR_CODES))

export function isErrorCode(value: string): value is ErrorCode {
  return errorCodeValues.has(value)
}

export function assertErrorCode(value: string): ErrorCode {
  if (isErrorCode(value)) return value

  console.error(
    JSON.stringify({
      event: 'api_error_code_unknown',
      error: value,
    }),
  )
  throw new Error(`Unknown API error code: ${value}`)
}
