# LLM Analyze + Scope File Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace keyword scope analysis with OpenAI via `POST /api/analyze`, and let users load project scope from `.txt` / `.md` / `.pdf` on New Project.

**Architecture:** Auth-gated analyze API loads the user-owned project, calls OpenAI `gpt-4o-mini` with strict JSON schema, validates into `AnalysisResult`. Client extracts upload text (pdf.js for PDF) into the existing scope textarea. No keyword fallback.

**Tech Stack:** Next.js 16 App Router, TypeScript, OpenAI Node SDK, pdfjs-dist, Vitest, existing Drizzle/Postgres auth, next-intl.

## Global Constraints

- Env var name for the key is exactly `OPENAI_API_KEY` (never invent alternate names).
- Model is `gpt-4o-mini`.
- Max upload size is 5 MiB; reject before reading.
- Formats only: `.txt`, `.md`, `.pdf`.
- Fail fast: missing key / OpenAI / invalid JSON → stable error keys; never call keyword `analyzeRequest`.
- Privacy UX: informational OpenAI notice near Check scope (no checkbox).
- Do not revert uncommitted EN/RU i18n work already in the tree; extend it.
- Prefer PowerShell for shell commands on Windows.
- No try/catch except around async I/O (OpenAI fetch, file read, JSON parse of request body already patterned in `readJsonObject`).
- No silent defaults for required analysis fields.

**Spec:** `docs/superpowers/specs/2026-08-17-llm-analyze-and-scope-upload-design.md`

## File Structure

| Path | Responsibility |
|---|---|
| `lib/llm/schema.ts` | Parse/validate unknown JSON → `AnalysisResult` |
| `lib/llm/prompt.ts` | Build system + user messages for OpenAI |
| `lib/llm/openai.ts` | Read `OPENAI_API_KEY`, call Chat Completions with json_schema |
| `lib/llm/analysis-json-schema.ts` | Strict JSON Schema object passed to OpenAI |
| `app/api/analyze/route.ts` | Auth, ownership, validate body, call LLM, return `{ result }` |
| `lib/scope/read-file.ts` | Client: file → text (txt/md/pdf), size/empty checks |
| `lib/analyze.ts` | Delete after store migration |
| `components/scope-guard/store.tsx` | `runCheck` → `/api/analyze` |
| `components/scope-guard/request-panel.tsx` | OpenAI notice; drop force-error example wiring if unused |
| `components/scope-guard/new-project-view.tsx` | Upload control |
| `lib/api/errors.ts` + `messages/en.json` + `messages/ru.json` | New error/UI keys |
| `.env.example` | Document `OPENAI_API_KEY` |
| `lib/llm/schema.test.ts` | Vitest for schema |
| `lib/scope/read-file.test.ts` | Vitest for txt/md + size reject |

---

### Task 1: Analysis schema validation + Vitest + error codes

**Files:**
- Create: `lib/llm/schema.ts`
- Create: `lib/llm/schema.test.ts`
- Modify: `lib/api/errors.ts`
- Modify: `messages/en.json`
- Modify: `messages/ru.json`
- Modify: `package.json` (add `vitest` devDependency + `"test": "vitest run"`)

**Interfaces:**
- Consumes: `AnalysisResult`, `Verdict`, `Tone` from `lib/types.ts`
- Produces: `parseAnalysisResult(value: unknown): AnalysisResult` — throws `Error` with message `invalid_analysis_result` if invalid

- [ ] **Step 1: Add Vitest**

```powershell
pnpm add -D vitest
```

In `package.json` scripts add:

```json
"test": "vitest run"
```

- [ ] **Step 2: Write failing tests**

Create `lib/llm/schema.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { parseAnalysisResult } from './schema'

const valid = {
  verdict: 'out_of_scope',
  confidence: 88,
  summary: 'Beyond scope.',
  reasoning: 'Adds pages excluded from scope.',
  citations: ['Additional pages beyond the 5 listed'],
  suggestion: 'Send a change order.',
  replies: {
    warm: 'Hi...',
    neutral: 'Hi...',
    firm: 'Hello...',
  },
  changeOrder: {
    description: '3 extra pages',
    timelineImpact: '+1 week',
    additionalCost: '$2400',
    note: 'Draft only.',
  },
}

describe('parseAnalysisResult', () => {
  it('accepts a full valid payload', () => {
    expect(parseAnalysisResult(valid).verdict).toBe('out_of_scope')
  })

  it('accepts missing optional suggestion', () => {
    const { suggestion: _s, ...rest } = valid
    expect(parseAnalysisResult(rest).suggestion).toBeUndefined()
  })

  it('rejects invalid verdict', () => {
    expect(() =>
      parseAnalysisResult({ ...valid, verdict: 'maybe' }),
    ).toThrow('invalid_analysis_result')
  })

  it('rejects non-object', () => {
    expect(() => parseAnalysisResult(null)).toThrow('invalid_analysis_result')
  })

  it('rejects incomplete replies', () => {
    expect(() =>
      parseAnalysisResult({
        ...valid,
        replies: { warm: 'a', neutral: 'b' },
      }),
    ).toThrow('invalid_analysis_result')
  })
})
```

- [ ] **Step 3: Run tests — expect FAIL**

```powershell
pnpm test
```

Expected: FAIL — cannot find module `./schema` or `parseAnalysisResult` is not a function.

- [ ] **Step 4: Implement `lib/llm/schema.ts`**

```ts
import type { AnalysisResult, Tone, Verdict } from '@/lib/types'

const VERDICTS = new Set<Verdict>(['in_scope', 'borderline', 'out_of_scope'])
const TONES: Tone[] = ['warm', 'neutral', 'firm']

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === 'string')
}

export function parseAnalysisResult(value: unknown): AnalysisResult {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('invalid_analysis_result')
  }

  const raw = value as Record<string, unknown>

  if (typeof raw.verdict !== 'string' || !VERDICTS.has(raw.verdict as Verdict)) {
    throw new Error('invalid_analysis_result')
  }
  if (typeof raw.confidence !== 'number' || !Number.isFinite(raw.confidence)) {
    throw new Error('invalid_analysis_result')
  }
  if (!isNonEmptyString(raw.summary) || !isNonEmptyString(raw.reasoning)) {
    throw new Error('invalid_analysis_result')
  }
  if (!isStringArray(raw.citations)) {
    throw new Error('invalid_analysis_result')
  }
  if (raw.suggestion !== undefined && typeof raw.suggestion !== 'string') {
    throw new Error('invalid_analysis_result')
  }
  if (!raw.replies || typeof raw.replies !== 'object' || Array.isArray(raw.replies)) {
    throw new Error('invalid_analysis_result')
  }
  const repliesRaw = raw.replies as Record<string, unknown>
  for (const tone of TONES) {
    if (!isNonEmptyString(repliesRaw[tone])) {
      throw new Error('invalid_analysis_result')
    }
  }
  if (
    !raw.changeOrder ||
    typeof raw.changeOrder !== 'object' ||
    Array.isArray(raw.changeOrder)
  ) {
    throw new Error('invalid_analysis_result')
  }
  const co = raw.changeOrder as Record<string, unknown>
  if (
    !isNonEmptyString(co.description) ||
    !isNonEmptyString(co.timelineImpact) ||
    !isNonEmptyString(co.additionalCost) ||
    !isNonEmptyString(co.note)
  ) {
    throw new Error('invalid_analysis_result')
  }

  const result: AnalysisResult = {
    verdict: raw.verdict as Verdict,
    confidence: raw.confidence,
    summary: raw.summary.trim(),
    reasoning: raw.reasoning.trim(),
    citations: raw.citations,
    replies: {
      warm: (repliesRaw.warm as string).trim(),
      neutral: (repliesRaw.neutral as string).trim(),
      firm: (repliesRaw.firm as string).trim(),
    },
    changeOrder: {
      description: co.description.trim(),
      timelineImpact: co.timelineImpact.trim(),
      additionalCost: co.additionalCost.trim(),
      note: co.note.trim(),
    },
  }

  if (typeof raw.suggestion === 'string' && raw.suggestion.trim().length > 0) {
    result.suggestion = raw.suggestion.trim()
  }

  return result
}
```

- [ ] **Step 5: Add error codes + message strings**

In `lib/api/errors.ts` add:

```ts
  analysisUnavailable: 'errors.analysisUnavailable',
  analysisFailed: 'errors.analysisFailed',
  scopeFileTooLarge: 'errors.scopeFileTooLarge',
  scopeFileUnsupported: 'errors.scopeFileUnsupported',
  scopeFileEmpty: 'errors.scopeFileEmpty',
```

In `messages/en.json` under `errors`:

```json
"analysisUnavailable": "Analysis is unavailable. Configure OPENAI_API_KEY and try again.",
"analysisFailed": "Scope analysis failed. Please try again.",
"scopeFileTooLarge": "File is larger than 5 MB.",
"scopeFileUnsupported": "Use a .txt, .md, or .pdf file.",
"scopeFileEmpty": "Could not extract text from this file."
```

In `messages/ru.json` under `errors` (Russian equivalents of the same keys).

Also add under `check` in both catalogs:

```json
"openaiNotice": "Checking sends this project's scope and your request text to OpenAI for analysis. Review the result before sending anything to your client."
```

RU: equivalent Russian copy.

Update `workspace.footer` in both catalogs so it no longer claims requests are “not analyzed by a real AI”. Replace with copy that states analysis uses OpenAI and results are suggestions, not legal advice.

- [ ] **Step 6: Run tests — expect PASS**

```powershell
pnpm test
pnpm exec tsc --noEmit
```

Expected: Vitest PASS; tsc clean.

- [ ] **Step 7: Commit**

```powershell
git add package.json pnpm-lock.yaml lib/llm/schema.ts lib/llm/schema.test.ts lib/api/errors.ts messages/en.json messages/ru.json
git commit -m "Add analysis result validation and LLM error message keys."
```

---

### Task 2: Prompt + OpenAI JSON schema + OpenAI client

**Files:**
- Create: `lib/llm/prompt.ts`
- Create: `lib/llm/analysis-json-schema.ts`
- Create: `lib/llm/openai.ts`
- Modify: `.env.example`
- Modify: `package.json` (add `openai` dependency)

**Interfaces:**
- Consumes: `parseAnalysisResult`, `Industry` from types
- Produces:
  - `buildAnalysisMessages(input: { scope: string; request: string; industry: Industry }): { role: 'system' | 'user'; content: string }[]`
  - `ANALYSIS_JSON_SCHEMA` — object suitable for `response_format.json_schema.schema`
  - `analyzeWithOpenAI(input: { scope: string; request: string; industry: Industry }): Promise<AnalysisResult>`
  - Throws `Error('openai_api_key_missing')` if `process.env.OPENAI_API_KEY` is missing/empty
  - Throws `Error('openai_request_failed')` on API/network/empty content failures after logging

- [ ] **Step 1: Install OpenAI SDK**

```powershell
pnpm add openai
```

Append to `.env.example`:

```
OPENAI_API_KEY=replace-with-your-openai-api-key
```

- [ ] **Step 2: Create `lib/llm/analysis-json-schema.ts`**

Export a strict schema matching `AnalysisResult` (all required except `suggestion` must be listed in `required`; for OpenAI strict mode, include `suggestion` as required but allow empty string — then strip empty in `parseAnalysisResult` OR make suggestion always required string and treat `""` as absent in parser). Prefer: require `suggestion` as string in schema; in `parseAnalysisResult` already treats empty as absent if you extend it — **update parser** so empty `suggestion: ""` is omitted (add one Vitest case in this task if needed).

```ts
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
    confidence: { type: 'number' },
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
```

Update `parseAnalysisResult` to accept `suggestion: ""` and omit it from the result (do not throw).

- [ ] **Step 3: Create `lib/llm/prompt.ts`**

```ts
import type { Industry } from '@/lib/types'

export function buildAnalysisMessages(input: {
  scope: string
  request: string
  industry: Industry
}) {
  const system = `You are Scope Creep Guard for freelancers.
Compare the client request ONLY against the provided project scope.
Industry context: ${input.industry}.
Return one verdict:
- in_scope: clearly covered by scope / included revisions
- out_of_scope: new deliverables or explicitly excluded work
- borderline: adjacent or unclear; do not pretend certainty
Rules:
- Cite short verbatim phrases from the scope in citations (0-3 items).
- Write replies.warm / replies.neutral / replies.firm in professional English the freelancer can send.
- Fill changeOrder for out_of_scope and borderline; for in_scope set cost to included / $0 style text.
- changeOrder.note must say this is a draft, not legal advice.
- Never invent scope clauses that are not in the provided scope.
- suggestion may be empty string when not needed.`

  const user = `PROJECT SCOPE:
${input.scope}

CLIENT REQUEST:
${input.request}`

  return [
    { role: 'system' as const, content: system },
    { role: 'user' as const, content: user },
  ]
}
```

- [ ] **Step 4: Create `lib/llm/openai.ts`**

```ts
import OpenAI from 'openai'
import type { Industry } from '@/lib/types'
import { ANALYSIS_JSON_SCHEMA } from './analysis-json-schema'
import { buildAnalysisMessages } from './prompt'
import { parseAnalysisResult } from './schema'

export async function analyzeWithOpenAI(input: {
  scope: string
  request: string
  industry: Industry
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

  let completion: OpenAI.Chat.Completions.ChatCompletion
  try {
    completion = await client.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: buildAnalysisMessages(input),
      response_format: {
        type: 'json_schema',
        json_schema: {
          name: 'scope_analysis',
          strict: true,
          schema: ANALYSIS_JSON_SCHEMA,
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

  const content = completion.choices[0]?.message?.content
  if (!content) {
    console.error(
      JSON.stringify({
        event: 'openai_empty_content',
        finishReason: completion.choices[0]?.finish_reason ?? null,
      }),
    )
    throw new Error('openai_request_failed')
  }

  let parsed: unknown
  try {
    parsed = JSON.parse(content)
  } catch (error) {
    console.error(
      JSON.stringify({
        event: 'openai_json_parse_failed',
        message: error instanceof Error ? error.message : 'Unknown JSON parse error',
      }),
    )
    throw new Error('openai_request_failed')
  }

  try {
    return parseAnalysisResult(parsed)
  } catch (error) {
    console.error(
      JSON.stringify({
        event: 'openai_analysis_shape_invalid',
        message: error instanceof Error ? error.message : 'invalid_analysis_result',
      }),
    )
    throw new Error('openai_request_failed')
  }
}
```

- [ ] **Step 5: Verify compile**

```powershell
pnpm test
pnpm exec tsc --noEmit
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add package.json pnpm-lock.yaml .env.example lib/llm/prompt.ts lib/llm/analysis-json-schema.ts lib/llm/openai.ts lib/llm/schema.ts lib/llm/schema.test.ts
git commit -m "Add OpenAI analysis client with structured JSON schema."
```

---

### Task 3: `POST /api/analyze` route

**Files:**
- Create: `app/api/analyze/route.ts`
- Create: `lib/llm/analyze-request.ts` (body validation helper)

**Interfaces:**
- Consumes: `getCurrentUser`, `loadProjectForUser`, `analyzeWithOpenAI`, `readJsonObject`, `jsonError`, `ERROR_CODES`
- Produces: `POST` → `200 { result: AnalysisResult }`  
  Body: `{ projectId: string, request: string }`  
  Errors: `401 authRequired`, `400 requestBodyInvalid|requestRequired|scopeRequired`, `404 projectNotFound`, `503 analysisUnavailable` (missing key), `502 analysisFailed` (OpenAI/shape)

Note: middleware already blocks unauthenticated `/api/*` with `401`; route still calls `getCurrentUser` like other project routes.

- [ ] **Step 1: Create body validator `lib/llm/analyze-request.ts`**

```ts
import { ERROR_CODES, type ErrorCode } from '@/lib/api/errors'

export function parseAnalyzeBody(body: Record<string, unknown>): {
  ok: true
  projectId: string
  request: string
} | { ok: false; error: ErrorCode } {
  if (typeof body.projectId !== 'string' || body.projectId.trim().length === 0) {
    return { ok: false, error: ERROR_CODES.requestBodyInvalid }
  }
  if (typeof body.request !== 'string' || body.request.trim().length === 0) {
    return { ok: false, error: ERROR_CODES.requestRequired }
  }
  return {
    ok: true,
    projectId: body.projectId.trim(),
    request: body.request.trim(),
  }
}
```

Use `projectNotFound` only after `loadProjectForUser` returns null.

- [ ] **Step 2: Create `app/api/analyze/route.ts`**

```ts
import { NextResponse } from 'next/server'
import { ERROR_CODES } from '@/lib/api/errors'
import { jsonError, readJsonObject } from '@/lib/api/json'
import { getCurrentUser } from '@/lib/auth/current-user'
import { parseAnalyzeBody } from '@/lib/llm/analyze-request'
import { analyzeWithOpenAI } from '@/lib/llm/openai'
import { loadProjectForUser } from '@/lib/projects/data'

export async function POST(request: Request) {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)

  const body = await readJsonObject(request)
  if (!body) return jsonError(ERROR_CODES.requestBodyInvalid, 400)

  const parsed = parseAnalyzeBody(body)
  if (!parsed.ok) return jsonError(parsed.error, 400)

  const project = await loadProjectForUser(parsed.projectId, user.id)
  if (!project) return jsonError(ERROR_CODES.projectNotFound, 404)

  if (project.scope.trim().length === 0) {
    return jsonError(ERROR_CODES.scopeRequired, 400)
  }

  try {
    const result = await analyzeWithOpenAI({
      scope: project.scope,
      request: parsed.request,
      industry: project.industry,
    })
    return NextResponse.json({ result })
  } catch (error) {
    const message = error instanceof Error ? error.message : 'unknown'
    console.error(
      JSON.stringify({
        event: 'analyze_route_failed',
        userId: user.id,
        projectId: project.id,
        message,
      }),
    )
    if (message === 'openai_api_key_missing') {
      return jsonError(ERROR_CODES.analysisUnavailable, 503)
    }
    return jsonError(ERROR_CODES.analysisFailed, 502)
  }
}
```

- [ ] **Step 3: Manual smoke without key**

Ensure `.env.local` has no `OPENAI_API_KEY` (or empty). Start app if needed, login, then:

```powershell
# After obtaining session cookie via browser login, or use Invoke-WebRequest with cookie jar.
# Minimal check: POST /api/analyze without cookie → 401
Invoke-WebRequest -Method POST -Uri http://localhost:3000/api/analyze -ContentType 'application/json' -Body '{"projectId":"x","request":"y"}' -SkipHttpErrorCheck
```

Expected: `401` with `errors.authRequired`.

With valid cookie + real projectId + no key: `503` `errors.analysisUnavailable`.

- [ ] **Step 4: Commit**

```powershell
git add app/api/analyze/route.ts lib/llm/analyze-request.ts
git commit -m "Add authenticated /api/analyze endpoint for OpenAI scope checks."
```

---

### Task 4: Wire client store to `/api/analyze` and remove keyword analyzer

**Files:**
- Modify: `components/scope-guard/store.tsx`
- Modify: `components/scope-guard/request-panel.tsx`
- Modify: `lib/mock-data.ts` (remove `error` example that forced local failure)
- Delete: `lib/analyze.ts`
- Grep for `analyzeRequest` / `AnalysisError` / `forceError` and remove leftovers

**Interfaces:**
- Consumes: `POST /api/analyze` → `{ result: AnalysisResult }`
- Produces: `runCheck` async path; on success persist history then `status: 'result'`; on API error keys show error state (existing)

- [ ] **Step 1: Update `runAnalysis` in store**

Replace local `analyzeRequest` with:

```ts
async function runAnalysis(project: Project, request: string) {
  try {
    const data = await apiFetch<{ result: AnalysisResult }>(
      '/api/analyze',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ projectId: project.id, request }),
      },
    )

    const analysis = data.result
    await persistHistory(project.id, {
      date: todayISO(),
      request,
      verdict: analysis.verdict,
      summary: analysis.summary,
    })
    setResult(analysis)
    setStatus('result')
  } catch (error) {
    console.error(
      JSON.stringify({
        event: 'scope_check_failed',
        projectId: project.id,
        message: error instanceof Error ? error.message : 'Unknown scope check error',
        status: error instanceof ApiError ? error.status : null,
      }),
    )
    if (error instanceof ApiError && error.status === 401) {
      router.replace('/login')
      return
    }
    setStatus('error')
  }
}
```

Remove `forceErrorRef`, `loadExample` second arg `forceError`, and the artificial `setTimeout(..., 1500)` delay (call `void runAnalysis(...)` immediately after setting loading). Keep short_scope client guard (`scope.length < 60`) as UX, not as LLM substitute.

Update `loadExample` to:

```ts
function loadExample(text: string) {
  setRequestText(text)
  setResult(null)
  setStatus('idle')
}
```

Update `StoreValue` / `request-panel` call sites accordingly.

- [ ] **Step 2: Remove error example from `lib/mock-data.ts`**

Delete the `error` entry from `EXAMPLE_REQUESTS`. Remove `examples.error` usage from request-panel map types. Keep `examples.error` message key unused or delete from en/ru.

- [ ] **Step 3: Show OpenAI notice in `request-panel.tsx`**

Above the Check scope button:

```tsx
<p className="text-xs leading-relaxed text-muted-foreground">
  {t('check.openaiNotice')}
</p>
```

- [ ] **Step 4: Delete `lib/analyze.ts` and fix imports**

```powershell
rg -n "analyzeRequest|AnalysisError|lib/analyze" --glob "*.{ts,tsx}"
```

Expected after cleanup: no matches.

- [ ] **Step 5: Verify**

```powershell
pnpm exec tsc --noEmit
pnpm lint
pnpm test
```

Expected: clean.

Manual: with `OPENAI_API_KEY` set, Check scope returns real verdict; without key, error state (not fake in_scope).

- [ ] **Step 6: Commit**

```powershell
git add components/scope-guard/store.tsx components/scope-guard/request-panel.tsx lib/mock-data.ts messages/en.json messages/ru.json
git rm lib/analyze.ts
git commit -m "Route scope checks through /api/analyze and remove keyword analyzer."
```

---

### Task 5: Client scope file reader + New Project upload UI

**Files:**
- Create: `lib/scope/read-file.ts`
- Create: `lib/scope/read-file.test.ts`
- Modify: `components/scope-guard/new-project-view.tsx`
- Modify: `package.json` (add `pdfjs-dist`)
- Modify: `messages/en.json`, `messages/ru.json` (upload labels)

**Interfaces:**
- Consumes: browser `File`
- Produces:
  - `MAX_SCOPE_FILE_BYTES = 5 * 1024 * 1024`
  - `readScopeFile(file: File): Promise<string>`
  - Throws `Error` with message equal to `ERROR_CODES.scopeFileTooLarge | scopeFileUnsupported | scopeFileEmpty` (stable keys)

- [ ] **Step 1: Install pdfjs-dist**

```powershell
pnpm add pdfjs-dist
```

- [ ] **Step 2: Write failing tests for txt path**

`lib/scope/read-file.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { ERROR_CODES } from '@/lib/api/errors'
import { MAX_SCOPE_FILE_BYTES, readScopeFile } from './read-file'

describe('readScopeFile', () => {
  it('reads a utf-8 text file', async () => {
    const file = new File(['Hello scope'], 'scope.txt', { type: 'text/plain' })
    await expect(readScopeFile(file)).resolves.toBe('Hello scope')
  })

  it('rejects oversized files before reading', async () => {
    const file = new File([new Uint8Array(MAX_SCOPE_FILE_BYTES + 1)], 'big.txt')
    await expect(readScopeFile(file)).rejects.toThrow(ERROR_CODES.scopeFileTooLarge)
  })

  it('rejects unsupported extensions', async () => {
    const file = new File(['x'], 'scope.docx')
    await expect(readScopeFile(file)).rejects.toThrow(
      ERROR_CODES.scopeFileUnsupported,
    )
  })

  it('rejects empty text extract', async () => {
    const file = new File(['   '], 'scope.md', { type: 'text/markdown' })
    await expect(readScopeFile(file)).rejects.toThrow(ERROR_CODES.scopeFileEmpty)
  })
})
```

- [ ] **Step 3: Run — expect FAIL**

```powershell
pnpm test
```

- [ ] **Step 4: Implement `lib/scope/read-file.ts`**

```ts
import { ERROR_CODES } from '@/lib/api/errors'

export const MAX_SCOPE_FILE_BYTES = 5 * 1024 * 1024

function extensionOf(name: string) {
  const idx = name.lastIndexOf('.')
  if (idx < 0) return ''
  return name.slice(idx).toLowerCase()
}

async function readPdfText(file: File): Promise<string> {
  const pdfjs = await import('pdfjs-dist')
  // Worker for browser; Vitest/jsdom may not need full render — if worker fails in tests, only cover txt in unit tests and exercise PDF manually.
  pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url,
  ).toString()

  const data = new Uint8Array(await file.arrayBuffer())
  const doc = await pdfjs.getDocument({ data }).promise
  const parts: string[] = []
  for (let pageNum = 1; pageNum <= doc.numPages; pageNum += 1) {
    const page = await doc.getPage(pageNum)
    const content = await page.getTextContent()
    const text = content.items
      .map((item) => ('str' in item ? item.str : ''))
      .join(' ')
    parts.push(text)
  }
  return parts.join('\n')
}

export async function readScopeFile(file: File): Promise<string> {
  if (file.size > MAX_SCOPE_FILE_BYTES) {
    throw new Error(ERROR_CODES.scopeFileTooLarge)
  }

  const ext = extensionOf(file.name)
  let text = ''

  if (ext === '.txt' || ext === '.md') {
    text = await file.text()
  } else if (ext === '.pdf') {
    try {
      text = await readPdfText(file)
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'scope_pdf_extract_failed',
          message: error instanceof Error ? error.message : 'Unknown PDF error',
        }),
      )
      throw new Error(ERROR_CODES.scopeFileEmpty)
    }
  } else {
    throw new Error(ERROR_CODES.scopeFileUnsupported)
  }

  const trimmed = text.replace(/\u0000/g, '').trim()
  if (trimmed.length === 0) {
    throw new Error(ERROR_CODES.scopeFileEmpty)
  }
  return trimmed
}
```

If Vitest fails on `import.meta.url` / pdf worker, keep PDF branch but ensure txt tests pass; document PDF as manual smoke.

- [ ] **Step 5: Wire New Project UI**

In `new-project-view.tsx`:

- Add hidden `<input type="file" accept=".txt,.md,.pdf,text/plain,application/pdf" />`
- Button `t('projects.uploadScope')` opens file picker
- On change: `readScopeFile(file)` → `setScope(text)`; on throw show `t(assertErrorCode(error.message))`
- Add i18n keys:
  - `projects.uploadScope`: "Upload scope file"
  - `projects.uploadHint`: "Accepts .txt, .md, or .pdf up to 5 MB. Text is copied into the field below; the file is not stored."

- [ ] **Step 6: Verify**

```powershell
pnpm test
pnpm exec tsc --noEmit
pnpm lint
```

Manual: upload a small `.txt` and a text PDF; scope textarea fills; oversized/unsupported files show translated errors; Save still posts text only.

- [ ] **Step 7: Commit**

```powershell
git add lib/scope/read-file.ts lib/scope/read-file.test.ts components/scope-guard/new-project-view.tsx package.json pnpm-lock.yaml messages/en.json messages/ru.json
git commit -m "Add scope file upload with client-side txt/md/pdf extraction."
```

---

### Task 6: Docs status + end-to-end verification

**Files:**
- Modify: `docs/status.md`
- Modify: `docs/plans.md` (append short section for this slice)
- Modify: `docs/test-plan.md` (append LLM + upload checks)

- [ ] **Step 1: Update docs**

`docs/status.md`: mark LLM analyze + scope upload as Done with validation commands.

`docs/test-plan.md` add:

- Upload `.txt` / `.pdf` into New Project; reject >5MB and `.docx`
- Check scope with valid `OPENAI_API_KEY` → verdict + replies + change order + history
- Missing key → `errors.analysisUnavailable` / error UI (no keyword verdict)
- User B cannot analyze User A project id (`404`)
- OpenAI notice visible; footer no longer claims “no real AI”

- [ ] **Step 2: Full verification**

```powershell
pnpm test
pnpm lint
pnpm exec tsc --noEmit
pnpm build
```

Live smoke with Docker Postgres + `.env.local` including `OPENAI_API_KEY`, `DATABASE_URL`, `AUTH_SECRET`.

- [ ] **Step 3: Commit**

```powershell
git add docs/status.md docs/plans.md docs/test-plan.md
git commit -m "Document LLM analyze and scope upload verification."
```

---

## Self-review vs spec

| Spec requirement | Task |
|---|---|
| OpenAI via `OPENAI_API_KEY` / `gpt-4o-mini` | Task 2 |
| `POST /api/analyze` auth + ownership | Task 3 |
| Structured `AnalysisResult` validation | Task 1–2 |
| No keyword fallback | Task 4 deletes `lib/analyze.ts` |
| OpenAI notice (no checkbox) | Task 4 |
| `.txt`/`.md`/`.pdf`, 5 MiB, client extract | Task 5 |
| Store text only in Postgres | Task 5 (no binary API) |
| Error keys `analysisUnavailable` / `analysisFailed` | Task 1 + 3 |
| Middleware auth for `/api/analyze` | Existing middleware; Task 3 |
| i18n EN/RU | Tasks 1, 4, 5 |
| Unit tests schema + file reader | Tasks 1, 5 |
| Docs / smoke | Task 6 |

No DOCX / extension / onboarding / billing included.
