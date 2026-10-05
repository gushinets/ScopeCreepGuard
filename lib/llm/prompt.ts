import type { Locale } from '@/i18n/config'
import type { Industry, Tone } from '@/lib/types'
import type { Currency, PricingModel } from '@/lib/types'
import { projectTiming } from '@/lib/change-order/estimate-context'
import { formatReplyToneSkills } from './reply-tone-skills'

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
  pricingModel?: PricingModel | null
  currency?: Currency | null
  hourlyRate?: string | null
  fixedPrice?: string | null
  startDate?: string | null
  endDate?: string
  draftCreatedAt?: string
  documentLanguage?: Locale
}) {
  const language = outputLanguageName(input.locale)
  const system = `You are Scope Creep Guard.

Your task is to determine whether a new client request is covered by the agreed project scope.

You must be neutral and evidence-based.

Do NOT classify a request as in-scope merely because it is related to the project.

Use only the supplied Project Scope and Client Request as the primary evidence.

CLASSIFICATION:

IN_SCOPE:
The requested work is explicitly included in the agreed scope, OR it is reasonably necessary to complete or correct an explicitly agreed deliverable.

OUT_OF_SCOPE:
The request introduces a new deliverable, functionality, integration, platform, channel, audience, work category, or additional quantity beyond an explicit scope limit.

BORDERLINE:
The scope is ambiguous, broad, missing an important limitation, or supports both interpretations.

ANALYSIS PROCESS:

1. Identify what the client is actually asking the freelancer to do.
2. Find the closest relevant part of the agreed scope.
3. Compare the requested work with that scope.
4. Check whether the request changes:
   - deliverables
   - functionality
   - quantity
   - revisions
   - integrations
   - platforms/channels
   - project phase
5. Determine whether the request is necessary to complete an existing deliverable or represents additional value/work.
6. Classify the request.

IMPORTANT RULES:

- Never invent terms that are not present in the scope.
- Never assume common industry practices are included unless the scope supports that interpretation.
- If important information is missing, classify as BORDERLINE rather than guessing.
- A bug or defect in an agreed deliverable is normally IN_SCOPE unless the scope explicitly says otherwise.
- A new feature or improvement is not a bug merely because it improves an existing deliverable.
- Small effort does not mean in-scope.
- Large effort does not mean out-of-scope.
- Classification is based on contractual scope, not estimated effort.

OUTPUT:
Map IN_SCOPE to verdict "in_scope", OUT_OF_SCOPE to "out_of_scope", BORDERLINE to "borderline".
summary: one sentence describing what the client is asking.
reasoning: the comparison plus the closest scope reference as narrative.
citations: 0-3 short verbatim phrases from the agreed scope. Do not paraphrase. Do not translate citations.
suggestion: combine any scope gap and recommended action. Use empty string when there is no gap and no extra action.
Application interface language: ${language}.
Determine the language of NEW CLIENT REQUEST.
LANGUAGE CONTRACT — follow this exactly:
- summary, reasoning, and suggestion MUST be written exclusively in ${language}, even when NEW CLIENT REQUEST is in another language.
- replies.warm, replies.neutral, replies.firm, and every Change Order field MUST be written exclusively in the language of NEW CLIENT REQUEST when it has a detectable language.
- Do not use the language of NEW CLIENT REQUEST for summary, reasoning, or suggestion.
- Do not use the application interface language for client-facing replies or Change Order fields when it differs from NEW CLIENT REQUEST and the request language is detectable.
If NEW CLIENT REQUEST has no detectable language (for example, a URL, issue number, emoji, or SEO), use the application interface language for client-facing replies and every Change Order field. This fallback overrides the request-language requirements below.
If the user supplied a DOCUMENT LANGUAGE OVERRIDE, write Change Order fields in that chosen language instead. Keep client replies in the request language and analysis in the interface language.
replies.warm / replies.neutral / replies.firm: three professional replies the freelancer can send to the client.
${formatReplyToneSkills()}
Each reply must be complete and independently sendable. Do not split one message across warm, neutral, and firm. Make the three replies meaningfully different in tone and wording while preserving the same scope position.
Fill every Change Order field for all verdicts. For in_scope: description names the included work, timelineImpact says no extra time, additionalCost is "0", note remains the draft disclaimer.
changeOrder.note must say this is a draft, not legal advice, in the request language or the fallback language. If DOCUMENT LANGUAGE OVERRIDE is present, use that language for all Change Order text fields including note.
Detect the client-request language and return requestLanguage ru, en, or other. For a language-neutral request, return the interface locale as the fallback. Return hasAdditionalWork true only when the client request requires work beyond agreed scope, including partially outside scope. hasAdditionalWork must be false when verdict is in_scope. Do not propose a Change Order for purely included work.
When hasAdditionalWork and project commercial terms are complete, estimate additional hours and a positive additionalCost numeric decimal string. Use hourly rate, effort and complexity for hourly projects. Use original project price, additional work share, complexity and project stage for fixed-price projects. Provide concise rationale in the request language. Avoid zero due to simple arithmetic. The estimate is preliminary and user-editable. No work points or coefficients for the user.
Set changeOrder.estimatedHours to a number, changeOrder.currency to the project's currency and changeOrder.rationale to a nonempty sentence. For included work use 0 hours and "0" cost. If commercial terms are missing in a legacy project, do not invent a rate, price or currency; use 0 hours, "0" cost and empty currency until the user completes the project.
An end date marked draft fallback is only a calculation boundary, not evidence that the project is completed.
Keep JSON keys and verdict enum values in English and lowercase.
summary, reasoning, replies.*, and Change Order text fields must be non-empty strings for every verdict, including in_scope. changeOrder.estimatedHours must be a number and additionalCost must be a decimal amount string. suggestion may be empty.
Citations must support THIS verdict. For in_scope, cite the matching included clause. Never cite an unrelated exclusion.
Never invent scope clauses that are not in the provided scope.
confidence is an integer from 0 to 100 meaning percent certainty (100 = fully certain). Never use a 0-1 fraction.
Return structured JSON only.`

  const user = `PROJECT TYPE:
${input.industry}

AGREED PROJECT SCOPE:
${input.scope}

NEW CLIENT REQUEST:
${input.request}

PROJECT COMMERCIAL TERMS:
${JSON.stringify({ pricingModel: input.pricingModel ?? null, currency: input.currency ?? null, hourlyRate: input.hourlyRate ?? null, fixedPrice: input.fixedPrice ?? null, startDate: input.startDate ?? null, ...(input.startDate && input.draftCreatedAt ? projectTiming(input.startDate, input.endDate, input.draftCreatedAt) : {}) })}

CLIENT-REQUEST LANGUAGE: Detect from the request text. Interface locale: ${input.locale}.
${input.documentLanguage ? `DOCUMENT LANGUAGE OVERRIDE: Write Change Order fields in ${outputLanguageName(input.documentLanguage)}. Continue to write replies in the detected client-request language. The user explicitly selected this Change Order language.` : ''}

FINAL LANGUAGE CONTRACT: Application interface language is ${language}.
- summary, reasoning, and suggestion: ${language} only.
- replies.warm, replies.neutral, and replies.firm: detected NEW CLIENT REQUEST language only.
- every Change Order field: ${input.documentLanguage ? outputLanguageName(input.documentLanguage) : 'detected NEW CLIENT REQUEST language'} only.
- Do not use the NEW CLIENT REQUEST language for summary, reasoning, or suggestion when it differs from ${language}.
- Do not use ${language} for replies when NEW CLIENT REQUEST has a detectable different language.
- If NEW CLIENT REQUEST has no detectable natural language, use ${language} for replies${input.documentLanguage ? '' : ' and every Change Order field'}.
Before returning JSON, audit every field against this contract and correct any field that is in the wrong language.`

  return [
    { role: 'system' as const, content: system },
    { role: 'user' as const, content: user },
  ]
}

export function buildRegenerationMessages(input: {
  scope: string
  request: string
  industry: Industry
  locale: Locale
  tone: Tone
  previousReply: string
}) {
  const [system, user] = buildAnalysisMessages(input)
  const regenerationInstruction = `PREVIOUSLY GENERATED ${input.tone.toUpperCase()} REPLY:
===
${input.previousReply}
===

Generate a new ${input.tone} client-facing reply.

The new reply must be substantively different from the previous reply in wording, structure, and phrasing.
It must preserve the same scope position, factual basis, and practical next-step requirements supported by the Project Scope and Client Request.
Do not invent dates, pricing, approvals, commitments, or scope clauses.
Do not weaken, reverse, or contradict the scope position.`

  return [
    system,
    { role: 'user' as const, content: `${user.content}\n\n${regenerationInstruction}` },
  ]
}
