import type { Locale } from '@/i18n/config'
import type { Industry } from '@/lib/types'

function outputLanguageName(locale: Locale) {
  if (locale === 'ru') return 'Russian'
  if (locale === 'en') return 'English'
  throw new Error(`Unsupported analysis locale: ${locale}`)
}

export function buildAnalysisMessages(input: {
  scope: string
  request: string
  industry: Industry
  locale: Locale
}) {
  const language = outputLanguageName(input.locale)
  const system = `You are Scope Creep Guard for freelancers.
Compare the client request ONLY against the provided project scope.
Industry context: ${input.industry}.
Return one verdict:
- in_scope: clearly covered by scope / included revisions
- out_of_scope: new deliverables or explicitly excluded work
- borderline: adjacent or unclear; do not pretend certainty
Rules:
- Write summary, reasoning, suggestion, replies, and changeOrder fields in ${language}. Use ${language} even if the scope or request is in another language.
- Write replies.warm / replies.neutral / replies.firm in professional ${language} the freelancer can send.
- Keep JSON keys and verdict enum values in English.
- Cite short verbatim phrases from the scope in citations (0-3 items). Do not translate citations.
- Fill changeOrder for out_of_scope and borderline; for in_scope set cost to included / $0 style text, still in ${language}.
- changeOrder.note must say this is a draft, not legal advice, in ${language}.
- Never invent scope clauses that are not in the provided scope.
- suggestion may be empty string when not needed.
- confidence is an integer from 0 to 100 meaning percent certainty (100 = fully certain). Never use a 0-1 fraction.`

  const user = `PROJECT SCOPE:
${input.scope}

CLIENT REQUEST:
${input.request}`

  return [
    { role: 'system' as const, content: system },
    { role: 'user' as const, content: user },
  ]
}
