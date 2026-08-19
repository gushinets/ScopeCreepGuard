# Scope Classification Prompt + GPT-5.4 nano Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Check-scope classification prompt with the evidence-based rules, and call OpenAI `gpt-5.4-nano` with medium reasoning through the Responses API, while keeping the existing `AnalysisResult` UI contract.

**Architecture:** `buildAnalysisMessages` still returns system + user strings. `analyzeWithOpenAI` maps those to Responses `instructions` / `input`, sets `reasoning.effort = "medium"`, enforces the existing strict `scope_analysis` JSON schema, and parses `output_text` with `parseAnalysisResult`. No UI, DB, or `/api/analyze` contract changes.

**Tech Stack:** Next.js 16 App Router, TypeScript, OpenAI Node SDK `^7.4.0` Responses API, Vitest, existing Drizzle/Postgres auth, next-intl.

## Global Constraints

- Env var name for the key is exactly `OPENAI_API_KEY` (never invent alternate names).
- Model is `gpt-5.4-nano`.
- Reasoning is on: `reasoning: { effort: "medium" }` (do not leave nano’s default `none`).
- One Responses API call per Check scope (`client.responses.create`), not Chat Completions.
- Verdict JSON values stay `in_scope` / `borderline` / `out_of_scope`.
- Keep current `AnalysisResult` (confidence, citations, suggestion, three reply tones, changeOrder).
- No conversation-context section in the user prompt.
- Fail fast: missing key / OpenAI / incomplete / invalid JSON → stable error keys; no retries; no keyword fallback.
- Do not log scope or the client request.
- Prefer PowerShell for shell commands on Windows.
- No try/catch except around async I/O and JSON parse of model output (same pattern as current `lib/llm/openai.ts`).
- No silent defaults for required analysis fields.

**Spec:** `docs/superpowers/specs/2026-08-19-scope-classification-prompt-design.md`

## File Structure

| Path | Responsibility |
|---|---|
| `lib/llm/prompt.ts` | Build system + user messages (new classification + output appendix) |
| `lib/llm/prompt.test.ts` | Vitest for prompt contents |
| `lib/llm/openai.ts` | Responses API call, incomplete/empty checks, parse `output_text` |
| `lib/llm/openai.test.ts` | Vitest for completed-output gating and usage log fields |
| `lib/llm/analysis-json-schema.ts` | Unchanged strict schema |
| `lib/llm/schema.ts` | Unchanged `parseAnalysisResult` |
| `app/api/analyze/route.ts` | Unchanged contract |
| `docs/status.md` | Record model + prompt slice as done |
| `docs/plans.md` | Short milestone for this slice |
| `docs/test-plan.md` | Prompt/model smoke notes |

Do not modify result UI, DB schema, or `/api/analyze` request/response shape.

---

### Task 1: Replace classification prompt

**Files:**
- Modify: `lib/llm/prompt.test.ts`
- Modify: `lib/llm/prompt.ts`

**Interfaces:**
- Consumes: `Locale` from `@/i18n/config`; `Industry` from `@/lib/types`
- Produces: `buildAnalysisMessages(input: { scope: string; request: string; industry: Industry; locale: Locale }): [{ role: 'system'; content: string }, { role: 'user'; content: string }]`

- [ ] **Step 1: Write the failing tests**

Replace `lib/llm/prompt.test.ts` entirely with:

```ts
import { describe, expect, it } from 'vitest'
import { buildAnalysisMessages } from './prompt'

const input = {
  scope: 'Build a landing page.',
  request: 'Add a blog.',
  industry: 'Development' as const,
}

describe('buildAnalysisMessages', () => {
  it('instructs the model to write generated fields in Russian when locale is ru', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'ru' })

    expect(system.content).toContain('Russian')
    expect(system.content).not.toContain('professional English')
    expect(system.content).toMatch(/summary|reasoning|replies|changeOrder/i)
  })

  it('instructs the model to write generated fields in English when locale is en', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'en' })

    expect(system.content).toContain('English')
    expect(system.content).toMatch(/summary|reasoning|replies|changeOrder/i)
  })

  it('keeps citations as verbatim scope phrases regardless of locale', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'ru' })

    expect(system.content.toLowerCase()).toMatch(/verbatim/)
    expect(system.content.toLowerCase()).toMatch(/do not translate/)
  })

  it('uses the evidence-based classification definitions and process', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'en' })

    expect(system.content).toContain('You are Scope Creep Guard.')
    expect(system.content).toMatch(/Do NOT classify a request as in-scope merely because it is related/i)
    expect(system.content).toContain('IN_SCOPE:')
    expect(system.content).toContain('OUT_OF_SCOPE:')
    expect(system.content).toContain('BORDERLINE:')
    expect(system.content).toMatch(/reasonably necessary to complete or correct/i)
    expect(system.content).toMatch(/Identify what the client is actually asking/i)
    expect(system.content).toMatch(/platforms\/channels/)
    expect(system.content).toMatch(/Never invent terms that are not present in the scope/i)
    expect(system.content).toMatch(/bug or defect in an agreed deliverable is normally IN_SCOPE/i)
    expect(system.content).toMatch(/new feature or improvement is not a bug/i)
    expect(system.content).toMatch(/Small effort does not mean in-scope/i)
    expect(system.content).toMatch(/Classification is based on contractual scope, not estimated effort/i)
  })

  it('maps classification labels onto lowercase verdict enums in the output appendix', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'en' })

    expect(system.content).toContain('in_scope')
    expect(system.content).toContain('out_of_scope')
    expect(system.content).toContain('borderline')
    expect(system.content).toMatch(/replies\.warm/)
    expect(system.content).toMatch(/replies\.neutral/)
    expect(system.content).toMatch(/replies\.firm/)
    expect(system.content).toMatch(/confidence is an integer from 0 to 100/i)
    expect(system.content.trim().endsWith('Return structured JSON only.')).toBe(
      true,
    )
  })

  it('requires non-empty changeOrder fields for every verdict including in_scope', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'en' })

    expect(system.content).toMatch(/non-empty/i)
    expect(system.content).toMatch(/every verdict/i)
    expect(system.content).toMatch(/in_scope/)
    expect(system.content).toMatch(/changeOrder/)
  })

  it('builds the labeled user prompt without conversation context', () => {
    const [, user] = buildAnalysisMessages({ ...input, locale: 'en' })

    expect(user.content).toContain('PROJECT TYPE:')
    expect(user.content).toContain('Development')
    expect(user.content).toContain('AGREED PROJECT SCOPE:')
    expect(user.content).toContain('Build a landing page.')
    expect(user.content).toContain('NEW CLIENT REQUEST:')
    expect(user.content).toContain('Add a blog.')
    expect(user.content).not.toMatch(/CONVERSATION CONTEXT/i)
    expect(user.content).not.toMatch(/^PROJECT SCOPE:/m)
    expect(user.content).not.toMatch(/^CLIENT REQUEST:/m)
  })

  it('drops the old listed-capability procedure and few-shot examples', () => {
    const [system] = buildAnalysisMessages({ ...input, locale: 'en' })

    expect(system.content).not.toMatch(/listed capability/i)
    expect(system.content).not.toMatch(/add the ability/i)
    expect(system.content).not.toMatch(/product backends/i)
    expect(system.content).not.toMatch(/3 more pages/i)
    expect(system.content).not.toMatch(/newsletter/i)
    expect(system.content).not.toMatch(/surface wording/i)
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
pnpm exec vitest run lib/llm/prompt.test.ts
```

Expected: FAIL. Current `prompt.ts` still has the old few-shots / listed-capability text and `PROJECT SCOPE:` / `CLIENT REQUEST:` user labels.

- [ ] **Step 3: Write the prompt implementation**

Replace `lib/llm/prompt.ts` entirely with:

```ts
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
replies.warm / replies.neutral / replies.firm: three professional ${language} replies the freelancer can send to the client.
Fill changeOrder in all verdicts, still in ${language}. For in_scope: description names the included work, timelineImpact is none / no extra time, additionalCost is included / $0, note remains the draft disclaimer.
changeOrder.note must say this is a draft, not legal advice, in ${language}.
Write summary, reasoning, suggestion, replies, and changeOrder fields in ${language}. Use ${language} even if the scope or request is in another language.
Keep JSON keys and verdict enum values in English and lowercase.
summary, reasoning, replies.*, and all changeOrder fields must be non-empty strings for every verdict, including in_scope. suggestion may be empty.
Citations must support THIS verdict. For in_scope, cite the matching included clause. Never cite an unrelated exclusion.
Never invent scope clauses that are not in the provided scope.
confidence is an integer from 0 to 100 meaning percent certainty (100 = fully certain). Never use a 0-1 fraction.
Return structured JSON only.`

  const user = `PROJECT TYPE:
${input.industry}

AGREED PROJECT SCOPE:
${input.scope}

NEW CLIENT REQUEST:
${input.request}`

  return [
    { role: 'system' as const, content: system },
    { role: 'user' as const, content: user },
  ]
}
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
pnpm exec vitest run lib/llm/prompt.test.ts
```

Expected: PASS (all tests in that file).

- [ ] **Step 5: Commit**

```powershell
git add lib/llm/prompt.ts lib/llm/prompt.test.ts
git commit -m @"
Replace scope classification prompt with evidence-based rules.
"@
```

---

### Task 2: Responses API, gpt-5.4-nano, medium reasoning

**Files:**
- Create: `lib/llm/openai.test.ts`
- Modify: `lib/llm/openai.ts`

**Interfaces:**
- Consumes: `buildAnalysisMessages` from Task 1; `ANALYSIS_JSON_SCHEMA` from `lib/llm/analysis-json-schema.ts`; `parseAnalysisResult` from `lib/llm/schema.ts`
- Produces:
  - `analyzeWithOpenAI(input: { scope: string; request: string; industry: Industry; locale: Locale }): Promise<AnalysisResult>`
  - `openaiUsageFields(usage: OpenAIAnalysisResponse['usage']): { inputTokens?: number; outputTokens?: number; reasoningTokens?: number }`
  - `requireCompletedOutputText(response: OpenAIAnalysisResponse): string` — throws `Error('openai_request_failed')` when `status !== 'completed'` or `output_text` is empty/whitespace

- [ ] **Step 1: Write the failing tests**

Create `lib/llm/openai.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import {
  openaiUsageFields,
  requireCompletedOutputText,
  type OpenAIAnalysisResponse,
} from './openai'

const completed: OpenAIAnalysisResponse = {
  status: 'completed',
  output_text: '{"verdict":"in_scope"}',
  incomplete_details: null,
  usage: {
    input_tokens: 100,
    output_tokens: 40,
    output_tokens_details: { reasoning_tokens: 12 },
  },
}

describe('openaiUsageFields', () => {
  it('returns input, output, and reasoning token counts when usage is present', () => {
    expect(openaiUsageFields(completed.usage)).toEqual({
      inputTokens: 100,
      outputTokens: 40,
      reasoningTokens: 12,
    })
  })

  it('returns an empty object when usage is missing', () => {
    expect(openaiUsageFields(undefined)).toEqual({})
  })
})

describe('requireCompletedOutputText', () => {
  it('returns output_text when status is completed', () => {
    expect(requireCompletedOutputText(completed)).toBe(
      '{"verdict":"in_scope"}',
    )
  })

  it('throws when status is not completed', () => {
    expect(() =>
      requireCompletedOutputText({
        ...completed,
        status: 'incomplete',
        incomplete_details: { reason: 'max_output_tokens' },
      }),
    ).toThrow('openai_request_failed')
  })

  it('throws when status is omitted', () => {
    const { status: _status, ...rest } = completed
    expect(() =>
      requireCompletedOutputText(rest as OpenAIAnalysisResponse),
    ).toThrow('openai_request_failed')
  })

  it('throws when output_text is empty or whitespace', () => {
    expect(() =>
      requireCompletedOutputText({ ...completed, output_text: '' }),
    ).toThrow('openai_request_failed')
    expect(() =>
      requireCompletedOutputText({ ...completed, output_text: '   ' }),
    ).toThrow('openai_request_failed')
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
pnpm exec vitest run lib/llm/openai.test.ts
```

Expected: FAIL with a module-export error (`openaiUsageFields` / `requireCompletedOutputText` / `OpenAIAnalysisResponse` are not exported).

- [ ] **Step 3: Implement Responses client + helpers**

Replace `lib/llm/openai.ts` entirely with:

```ts
import OpenAI from 'openai'
import type { Locale } from '@/i18n/config'
import type { Industry } from '@/lib/types'
import { ANALYSIS_JSON_SCHEMA } from './analysis-json-schema'
import { buildAnalysisMessages } from './prompt'
import { parseAnalysisResult } from './schema'

const ANALYSIS_JSON_SCHEMA_RECORD = ANALYSIS_JSON_SCHEMA as unknown as {
  [key: string]: unknown
}

export type OpenAIAnalysisResponse = {
  status?:
    | 'completed'
    | 'failed'
    | 'in_progress'
    | 'cancelled'
    | 'queued'
    | 'incomplete'
  output_text: string
  incomplete_details: { reason?: 'max_output_tokens' | 'content_filter' } | null
  usage?: {
    input_tokens: number
    output_tokens: number
    output_tokens_details: { reasoning_tokens: number }
  }
}

export function openaiUsageFields(usage: OpenAIAnalysisResponse['usage']) {
  if (!usage) {
    return {}
  }
  return {
    inputTokens: usage.input_tokens,
    outputTokens: usage.output_tokens,
    reasoningTokens: usage.output_tokens_details.reasoning_tokens,
  }
}

export function requireCompletedOutputText(
  response: OpenAIAnalysisResponse,
): string {
  if (response.status !== 'completed') {
    console.error(
      JSON.stringify({
        event: 'openai_incomplete',
        status: response.status ?? null,
        incompleteReason: response.incomplete_details?.reason ?? null,
        ...openaiUsageFields(response.usage),
      }),
    )
    throw new Error('openai_request_failed')
  }

  if (response.output_text.trim().length === 0) {
    console.error(
      JSON.stringify({
        event: 'openai_empty_content',
        status: response.status,
        ...openaiUsageFields(response.usage),
      }),
    )
    throw new Error('openai_request_failed')
  }

  return response.output_text
}

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
  const [system, user] = buildAnalysisMessages(input)

  let response: OpenAI.Responses.Response
  try {
    response = await client.responses.create({
      model: 'gpt-5.4-nano',
      reasoning: { effort: 'medium' },
      instructions: system.content,
      input: user.content,
      text: {
        format: {
          type: 'json_schema',
          name: 'scope_analysis',
          strict: true,
          schema: ANALYSIS_JSON_SCHEMA_RECORD,
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

  const content = requireCompletedOutputText(response)

  let parsed: unknown
  try {
    parsed = JSON.parse(content)
  } catch (error) {
    console.error(
      JSON.stringify({
        event: 'openai_json_parse_failed',
        message: error instanceof Error ? error.message : 'Unknown JSON parse error',
        ...openaiUsageFields(response.usage),
      }),
    )
    throw new Error('openai_request_failed')
  }

  try {
    return parseAnalysisResult(parsed)
  } catch (error) {
    const keys =
      parsed && typeof parsed === 'object' && !Array.isArray(parsed)
        ? Object.keys(parsed)
        : []
    console.error(
      JSON.stringify({
        event: 'openai_analysis_shape_invalid',
        message: error instanceof Error ? error.message : 'invalid_analysis_result',
        keys,
        ...openaiUsageFields(response.usage),
      }),
    )
    throw new Error('openai_request_failed')
  }
}
```

`app/api/analyze/route.ts` stays unchanged: missing key still maps to `errors.analysisUnavailable`; every `openai_request_failed` still maps to `errors.analysisFailed`.

- [ ] **Step 4: Run tests to verify they pass**

```powershell
pnpm exec vitest run lib/llm/openai.test.ts lib/llm/prompt.test.ts lib/llm/schema.test.ts
pnpm exec tsc --noEmit
```

Expected: PASS. `tsc` reports no errors. Do not leave `gpt-4o-mini` or `chat.completions.create` in `lib/llm/openai.ts`.

- [ ] **Step 5: Commit**

```powershell
git add lib/llm/openai.ts lib/llm/openai.test.ts
git commit -m @"
Switch scope analysis to GPT-5.4 nano with Responses reasoning.
"@
```

---

### Task 3: Docs and verification

**Files:**
- Modify: `docs/status.md`
- Modify: `docs/plans.md`
- Modify: `docs/test-plan.md`

**Interfaces:**
- Consumes: Task 1 prompt + Task 2 OpenAI client
- Produces: docs that name `gpt-5.4-nano`, medium reasoning, and the new prompt labels

- [ ] **Step 1: Update docs**

In `docs/status.md`:

- Change the current-phase / Done bullets that say `gpt-4o-mini` / Chat Completions so they describe `gpt-5.4-nano`, Responses API, `reasoning.effort = medium`, and the evidence-based classification prompt.
- Keep prior auth/upload facts. Do not invent a live-smoke result for this slice unless you actually ran it.

Append to `docs/plans.md`:

```md
# Scope Classification Prompt + GPT-5.4 nano

## Goal

Replace Check-scope classification rules and switch the OpenAI call to `gpt-5.4-nano` with medium reasoning, without changing the result UI contract.

## Milestones

### 1. Prompt

- Evidence-based IN_SCOPE / OUT_OF_SCOPE / BORDERLINE system prompt.
- User prompt labels: PROJECT TYPE, AGREED PROJECT SCOPE, NEW CLIENT REQUEST.
- Output appendix maps onto existing `AnalysisResult` fields.

### 2. Model call

- `client.responses.create`, model `gpt-5.4-nano`, `reasoning.effort = medium`.
- Fail incomplete / empty / invalid JSON with `errors.analysisFailed`.

Definition of done: Check scope uses the new rules on `gpt-5.4-nano`; UI still shows confidence, three tones, Change Order, and history.

Validation:

- `pnpm test`
- `pnpm lint`
- `pnpm exec tsc --noEmit`
```

In `docs/test-plan.md`, under the LLM analyze section, add:

- Check scope uses `gpt-5.4-nano` with reasoning; result still includes verdict, three replies, Change Order, and history.
- Prompt regression: `pnpm exec vitest run lib/llm/prompt.test.ts` (new labels present; old few-shots absent).
- Incomplete model responses surface `errors.analysisFailed` (no fabricated verdict).

- [ ] **Step 2: Full verification**

```powershell
pnpm test
pnpm lint
pnpm exec tsc --noEmit
```

Expected: all commands succeed.

Live smoke (manual, only if `.env.local` has `OPENAI_API_KEY`): Check scope on the Acme examples for in / borderline / out; confirm verdict, three replies, Change Order, history. Missing key still shows `errors.analysisUnavailable`. Do not claim live smoke passed if it was not run.

- [ ] **Step 3: Commit**

```powershell
git add docs/status.md docs/plans.md docs/test-plan.md
git commit -m @"
Document GPT-5.4 nano classification prompt verification.
"@
```

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|---|---|
| Replace classification prompt verbatim + output appendix | Task 1 |
| User prompt PROJECT TYPE / AGREED SCOPE / NEW REQUEST; no conversation context | Task 1 |
| Drop old few-shots / listed-capability procedure | Task 1 |
| Keep `AnalysisResult` / UI / DB / analyze route contract | Tasks 1–2 (no edits there) |
| `gpt-5.4-nano` + Responses API + `reasoning.effort = medium` | Task 2 |
| Read `output_text`; fail incomplete/empty/invalid JSON | Task 2 |
| Log status, incomplete reason, token usage; never log scope/request | Task 2 |
| Missing key → `analysisUnavailable`; other OpenAI failures → `analysisFailed` | Task 2 (route unchanged) |
| Prompt unit tests + schema tests unchanged + regression commands | Tasks 1–3 |
| Docs / live smoke notes | Task 3 |
