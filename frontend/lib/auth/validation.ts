import { ERROR_CODES, type ErrorCode } from '@/lib/api/errors'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const MIN_PASSWORD_LENGTH = 8

export interface CredentialsInput {
  email: unknown
  password: unknown
}

export interface Credentials {
  email: string
  password: string
}

export type CredentialsValidationResult =
  | { ok: true; credentials: Credentials }
  | { ok: false; error: ErrorCode }

export function normalizeEmail(email: string) {
  return email.trim().toLowerCase()
}

export function parseCredentials(
  input: CredentialsInput,
): CredentialsValidationResult {
  if (typeof input.email !== 'string') {
    return { ok: false, error: ERROR_CODES.emailRequired }
  }
  if (typeof input.password !== 'string') {
    return { ok: false, error: ERROR_CODES.passwordRequired }
  }

  const email = normalizeEmail(input.email)
  const password = input.password

  if (!EMAIL_PATTERN.test(email)) {
    return { ok: false, error: ERROR_CODES.invalidEmail }
  }
  if (password.length < MIN_PASSWORD_LENGTH) {
    return { ok: false, error: ERROR_CODES.passwordTooShort }
  }

  return { ok: true, credentials: { email, password } }
}
