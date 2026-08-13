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
  | { ok: false; error: string }

export function normalizeEmail(email: string) {
  return email.trim().toLowerCase()
}

export function parseCredentials(
  input: CredentialsInput,
): CredentialsValidationResult {
  if (typeof input.email !== 'string') {
    return { ok: false, error: 'Email is required.' }
  }
  if (typeof input.password !== 'string') {
    return { ok: false, error: 'Password is required.' }
  }

  const email = normalizeEmail(input.email)
  const password = input.password

  if (!EMAIL_PATTERN.test(email)) {
    return { ok: false, error: 'Enter a valid email address.' }
  }
  if (password.length < MIN_PASSWORD_LENGTH) {
    return { ok: false, error: 'Password must be at least 8 characters.' }
  }

  return { ok: true, credentials: { email, password } }
}
