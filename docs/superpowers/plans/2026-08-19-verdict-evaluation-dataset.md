# Verdict Evaluation Dataset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After each Check-scope verdict, the signed-in user can mark it Correct / Wrong / Debatable, persist a frozen evaluation snapshot, and download only their cases as JSONL.

**Architecture:** Result panel posts `{ historyEntryId, accuracy, humanVerdict?, aiReasoning }` to `POST /api/evaluations`. The server loads the owned history+project, snapshots scope/request/verdict/industry, upserts `evaluation_cases` on `history_entry_id`, and `GET /api/evaluations/export` returns that user’s six-field JSONL. No dashboard.

**Tech Stack:** Next.js 16 App Router, TypeScript, Drizzle ORM + Postgres, session cookies, next-intl, Vitest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-19-verdict-evaluation-dataset-design.md`
- Isolation: a user labels and exports only their own cases.
- Labeling surface: fresh result panel only (not History cards).
- Debatable: no expected verdict; JSONL `"human_verdict": null`.
- Correct: server sets `human_verdict` = history `ai_verdict`; client omits `humanVerdict`.
- Wrong: client sends a different expected verdict; same-as-AI is `errors.evaluationLabelInvalid`.
- JSONL keys only, in this order: `scope`, `request`, `ai_verdict`, `human_verdict`, `ai_reasoning`, `project_type`.
- JSONL verdicts: `IN_SCOPE` / `BORDERLINE` / `OUT_OF_SCOPE`. Industry: `development` / `design` / `marketing`.
- `accuracy` is DB-only, never in JSONL.
- Success upsert always HTTP `200`. Empty export: `200` and zero-byte body.
- Fail fast: no retries, no chained defaults for required fields, no invented `human_verdict` on Debatable.
- Do not log `scope`, `request`, or `ai_reasoning`.
- Prefer PowerShell for shell commands.
- No try/catch except around async I/O (fetch, JSON parse of request body already in `readJsonObject`, export query rethrow).
- Never rename env vars.
- If `docs/superpowers/specs/2026-08-19-verdict-evaluation-dataset-design.md` is uncommitted, include it in the first commit that adds code.

## File Structure

| Path | Responsibility |
|---|---|
| `lib/types.ts` | Add `EvaluationAccuracy` |
| `lib/api/errors.ts` | Add evaluation error codes |
| `lib/evaluations/validation.ts` | Parse POST body; `resolveHumanVerdict` |
| `lib/evaluations/validation.test.ts` | Vitest for parse + resolve |
| `lib/evaluations/export.ts` | Map DB row → six-field JSONL object + serialize |
| `lib/evaluations/export.test.ts` | Vitest for mapping and key order |
| `lib/evaluations/data.ts` | Load owned history+project; upsert; list for export |
| `lib/db/schema.ts` | `evaluation_accuracy` enum + `evaluation_cases` |
| `drizzle/` | Generated migration (do not hand-write SQL) |
| `app/api/evaluations/route.ts` | `POST` upsert |
| `app/api/evaluations/export/route.ts` | `GET` JSONL |
| `components/scope-guard/verdict-feedback.tsx` | Feedback card |
| `components/scope-guard/result-panel.tsx` | Mount card after Why, before verify warning |
| `components/scope-guard/store.tsx` | `currentHistoryEntryId`, `submitEvaluation`, `downloadEvaluationsExport` |
| `components/scope-guard/history-view.tsx` | Download JSONL button |
| `messages/en.json`, `messages/ru.json` | Feedback, export, error strings |
| `docs/status.md`, `docs/plans.md`, `docs/test-plan.md` | Record the slice |
| `middleware.ts` | No change |

Do not change analyze/prompt/history table contract, verdict banner, or add a dashboard.

---

### Task 1: Validation and error codes

**Files:**
- Modify: `lib/api/errors.ts`
- Modify: `lib/types.ts`
- Create: `lib/evaluations/validation.test.ts`
- Create: `lib/evaluations/validation.ts`

**Interfaces:**
- Consumes: `ErrorCode` pattern from `lib/api/errors.ts`; `Verdict` from `lib/types.ts`
- Produces:
  - `export type EvaluationAccuracy = 'correct' | 'wrong' | 'debatable'`
  - `export type EvaluationLabelParsed = { historyEntryId: string; accuracy: 'correct' | 'debatable'; aiReasoning: string } | { historyEntryId: string; accuracy: 'wrong'; humanVerdict: Verdict; aiReasoning: string }`
  - `export function parseEvaluationInput(body: Record<string, unknown>): { ok: true; label: EvaluationLabelParsed } | { ok: false; error: ErrorCode; status: 400 | 404 }`
  - `export function resolveHumanVerdict(parsed: EvaluationLabelParsed, aiVerdict: Verdict): { ok: true; humanVerdict: Verdict | null } | { ok: false; error: ErrorCode }`
  - Error codes: `errors.evaluationReasoningRequired`, `errors.evaluationLabelInvalid`, `errors.evaluationHistoryNotFound`

- [ ] **Step 1: Add error codes and `EvaluationAccuracy`**

In `lib/types.ts`, after `export type Verdict = 'in_scope' | 'borderline' | 'out_of_scope'`, add:

```ts
export type EvaluationAccuracy = 'correct' | 'wrong' | 'debatable'
```

In `lib/api/errors.ts`, add these keys next to the other error codes (before `} as const`):

```ts
  evaluationReasoningRequired: 'errors.evaluationReasoningRequired',
  evaluationLabelInvalid: 'errors.evaluationLabelInvalid',
  evaluationHistoryNotFound: 'errors.evaluationHistoryNotFound',
```

- [ ] **Step 2: Write the failing tests**

Create `lib/evaluations/validation.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { ERROR_CODES } from '@/lib/api/errors'
import { parseEvaluationInput, resolveHumanVerdict } from './validation'

const historyEntryId = '11111111-1111-4111-8111-111111111111'
const reasoning = 'The request adds a new deliverable.'

describe('parseEvaluationInput', () => {
  it('accepts correct without humanVerdict', () => {
    const parsed = parseEvaluationInput({
      historyEntryId,
      accuracy: 'correct',
      aiReasoning: reasoning,
    })
    expect(parsed).toEqual({
      ok: true,
      label: {
        historyEntryId,
        accuracy: 'correct',
        aiReasoning: reasoning,
      },
    })
  })

  it('accepts debatable without humanVerdict', () => {
    const parsed = parseEvaluationInput({
      historyEntryId,
      accuracy: 'debatable',
      aiReasoning: `  ${reasoning}  `,
    })
    expect(parsed.ok).toBe(true)
    if (!parsed.ok) return
    expect(parsed.label.accuracy).toBe('debatable')
    expect(parsed.label.aiReasoning).toBe(reasoning)
  })

  it('accepts wrong with a different expected verdict', () => {
    const parsed = parseEvaluationInput({
      historyEntryId,
      accuracy: 'wrong',
      humanVerdict: 'in_scope',
      aiReasoning: reasoning,
    })
    expect(parsed).toEqual({
      ok: true,
      label: {
        historyEntryId,
        accuracy: 'wrong',
        humanVerdict: 'in_scope',
        aiReasoning: reasoning,
      },
    })
  })

  it('rejects correct when humanVerdict is present', () => {
    const parsed = parseEvaluationInput({
      historyEntryId,
      accuracy: 'correct',
      humanVerdict: 'in_scope',
      aiReasoning: reasoning,
    })
    expect(parsed).toEqual({
      ok: false,
      error: ERROR_CODES.evaluationLabelInvalid,
      status: 400,
    })
  })

  it('rejects debatable when humanVerdict is present', () => {
    const parsed = parseEvaluationInput({
      historyEntryId,
      accuracy: 'debatable',
      humanVerdict: 'borderline',
      aiReasoning: reasoning,
    })
    expect(parsed.ok).toBe(false)
    if (parsed.ok) return
    expect(parsed.error).toBe(ERROR_CODES.evaluationLabelInvalid)
    expect(parsed.status).toBe(400)
  })

  it('rejects wrong without humanVerdict', () => {
    const parsed = parseEvaluationInput({
      historyEntryId,
      accuracy: 'wrong',
      aiReasoning: reasoning,
    })
    expect(parsed).toEqual({
      ok: false,
      error: ERROR_CODES.evaluationLabelInvalid,
      status: 400,
    })
  })

  it('rejects wrong when humanVerdict is null', () => {
    const parsed = parseEvaluationInput({
      historyEntryId,
      accuracy: 'wrong',
      humanVerdict: null,
      aiReasoning: reasoning,
    })
    expect(parsed.ok).toBe(false)
    if (parsed.ok) return
    expect(parsed.error).toBe(ERROR_CODES.evaluationLabelInvalid)
  })

  it('rejects invalid accuracy', () => {
    const parsed = parseEvaluationInput({
      historyEntryId,
      accuracy: 'maybe',
      aiReasoning: reasoning,
    })
    expect(parsed).toEqual({
      ok: false,
      error: ERROR_CODES.evaluationLabelInvalid,
      status: 400,
    })
  })

  it('rejects empty reasoning', () => {
    const parsed = parseEvaluationInput({
      historyEntryId,
      accuracy: 'correct',
      aiReasoning: '   ',
    })
    expect(parsed).toEqual({
      ok: false,
      error: ERROR_CODES.evaluationReasoningRequired,
      status: 400,
    })
  })

  it('rejects invalid historyEntryId as not found', () => {
    const parsed = parseEvaluationInput({
      historyEntryId: 'not-a-uuid',
      accuracy: 'correct',
      aiReasoning: reasoning,
    })
    expect(parsed).toEqual({
      ok: false,
      error: ERROR_CODES.evaluationHistoryNotFound,
      status: 404,
    })
  })
})

describe('resolveHumanVerdict', () => {
  it('sets human verdict equal to AI verdict for correct', () => {
    const resolved = resolveHumanVerdict(
      {
        historyEntryId,
        accuracy: 'correct',
        aiReasoning: reasoning,
      },
      'out_of_scope',
    )
    expect(resolved).toEqual({ ok: true, humanVerdict: 'out_of_scope' })
  })

  it('sets human verdict null for debatable', () => {
    const resolved = resolveHumanVerdict(
      {
        historyEntryId,
        accuracy: 'debatable',
        aiReasoning: reasoning,
      },
      'borderline',
    )
    expect(resolved).toEqual({ ok: true, humanVerdict: null })
  })

  it('keeps the expected verdict for wrong when it differs', () => {
    const resolved = resolveHumanVerdict(
      {
        historyEntryId,
        accuracy: 'wrong',
        humanVerdict: 'in_scope',
        aiReasoning: reasoning,
      },
      'out_of_scope',
    )
    expect(resolved).toEqual({ ok: true, humanVerdict: 'in_scope' })
  })

  it('rejects wrong when expected verdict equals the AI verdict', () => {
    const resolved = resolveHumanVerdict(
      {
        historyEntryId,
        accuracy: 'wrong',
        humanVerdict: 'out_of_scope',
        aiReasoning: reasoning,
      },
      'out_of_scope',
    )
    expect(resolved).toEqual({
      ok: false,
      error: ERROR_CODES.evaluationLabelInvalid,
    })
  })
})
```

- [ ] **Step 3: Run tests to verify they fail**

```powershell
pnpm exec vitest run lib/evaluations/validation.test.ts
```

Expected: FAIL — `Cannot find module './validation'` (or `parseEvaluationInput` is not exported).

- [ ] **Step 4: Write the implementation**

Create `lib/evaluations/validation.ts`:

```ts
import { ERROR_CODES, type ErrorCode } from '@/lib/api/errors'
import type { EvaluationAccuracy, Verdict } from '@/lib/types'

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const ACCURACIES = new Set<EvaluationAccuracy>(['correct', 'wrong', 'debatable'])
const VERDICTS = new Set<Verdict>(['in_scope', 'borderline', 'out_of_scope'])

export type EvaluationLabelParsed =
  | {
      historyEntryId: string
      accuracy: 'correct' | 'debatable'
      aiReasoning: string
    }
  | {
      historyEntryId: string
      accuracy: 'wrong'
      humanVerdict: Verdict
      aiReasoning: string
    }

export type EvaluationParseResult =
  | { ok: true; label: EvaluationLabelParsed }
  | { ok: false; error: ErrorCode; status: 400 | 404 }

export type HumanVerdictResult =
  | { ok: true; humanVerdict: Verdict | null }
  | { ok: false; error: ErrorCode }

function hasHumanVerdictKey(body: Record<string, unknown>) {
  return Object.prototype.hasOwnProperty.call(body, 'humanVerdict')
}

export function parseEvaluationInput(
  body: Record<string, unknown>,
): EvaluationParseResult {
  if (typeof body.historyEntryId !== 'string' || !UUID_PATTERN.test(body.historyEntryId)) {
    return {
      ok: false,
      error: ERROR_CODES.evaluationHistoryNotFound,
      status: 404,
    }
  }

  if (typeof body.aiReasoning !== 'string' || body.aiReasoning.trim().length === 0) {
    return {
      ok: false,
      error: ERROR_CODES.evaluationReasoningRequired,
      status: 400,
    }
  }

  if (typeof body.accuracy !== 'string' || !ACCURACIES.has(body.accuracy as EvaluationAccuracy)) {
    return {
      ok: false,
      error: ERROR_CODES.evaluationLabelInvalid,
      status: 400,
    }
  }

  const accuracy = body.accuracy as EvaluationAccuracy
  const aiReasoning = body.aiReasoning.trim()
  const historyEntryId = body.historyEntryId
  const humanVerdictPresent = hasHumanVerdictKey(body)

  if (accuracy === 'wrong') {
    if (
      typeof body.humanVerdict !== 'string' ||
      !VERDICTS.has(body.humanVerdict as Verdict)
    ) {
      return {
        ok: false,
        error: ERROR_CODES.evaluationLabelInvalid,
        status: 400,
      }
    }
    return {
      ok: true,
      label: {
        historyEntryId,
        accuracy: 'wrong',
        humanVerdict: body.humanVerdict as Verdict,
        aiReasoning,
      },
    }
  }

  if (humanVerdictPresent) {
    return {
      ok: false,
      error: ERROR_CODES.evaluationLabelInvalid,
      status: 400,
    }
  }

  return {
    ok: true,
    label: {
      historyEntryId,
      accuracy,
      aiReasoning,
    },
  }
}

export function resolveHumanVerdict(
  parsed: EvaluationLabelParsed,
  aiVerdict: Verdict,
): HumanVerdictResult {
  if (parsed.accuracy === 'debatable') {
    return { ok: true, humanVerdict: null }
  }
  if (parsed.accuracy === 'correct') {
    return { ok: true, humanVerdict: aiVerdict }
  }
  if (parsed.humanVerdict === aiVerdict) {
    return { ok: false, error: ERROR_CODES.evaluationLabelInvalid }
  }
  return { ok: true, humanVerdict: parsed.humanVerdict }
}
```

- [ ] **Step 5: Run tests to verify they pass**

```powershell
pnpm exec vitest run lib/evaluations/validation.test.ts
```

Expected: PASS (all tests).

- [ ] **Step 6: Commit**

```powershell
git add lib/api/errors.ts lib/types.ts lib/evaluations/validation.ts lib/evaluations/validation.test.ts docs/superpowers/specs/2026-08-19-verdict-evaluation-dataset-design.md
git commit -m @"
Add evaluation label validation for Correct, Wrong, and Debatable.
"@
```

---

### Task 2: JSONL export mapper

**Files:**
- Create: `lib/evaluations/export.test.ts`
- Create: `lib/evaluations/export.ts`

**Interfaces:**
- Consumes: `Verdict`, `Industry` from `@/lib/types`
- Produces:
  - `export type JsonlVerdict = 'IN_SCOPE' | 'BORDERLINE' | 'OUT_OF_SCOPE'`
  - `export type JsonlProjectType = 'development' | 'design' | 'marketing'`
  - `export interface EvaluationJsonlRecord { scope: string; request: string; ai_verdict: JsonlVerdict; human_verdict: JsonlVerdict | null; ai_reasoning: string; project_type: JsonlProjectType }`
  - `export function toEvaluationJsonlRecord(row: { scope: string; request: string; aiVerdict: Verdict; humanVerdict: Verdict | null; aiReasoning: string; industry: Industry }): EvaluationJsonlRecord`
  - `export function serializeEvaluationJsonl(records: EvaluationJsonlRecord[]): string`

- [ ] **Step 1: Write the failing tests**

Create `lib/evaluations/export.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { serializeEvaluationJsonl, toEvaluationJsonlRecord } from './export'

const baseRow = {
  scope: 'Build a 5-page marketing site.',
  request: 'Add 3 extra pages.',
  aiVerdict: 'out_of_scope' as const,
  humanVerdict: 'in_scope' as const,
  aiReasoning: 'Extra pages exceed the page limit.',
  industry: 'Development' as const,
}

describe('toEvaluationJsonlRecord', () => {
  it('maps DB verdicts and industry into the JSONL contract', () => {
    const record = toEvaluationJsonlRecord(baseRow)
    expect(record).toEqual({
      scope: 'Build a 5-page marketing site.',
      request: 'Add 3 extra pages.',
      ai_verdict: 'OUT_OF_SCOPE',
      human_verdict: 'IN_SCOPE',
      ai_reasoning: 'Extra pages exceed the page limit.',
      project_type: 'development',
    })
    expect(Object.keys(record)).toEqual([
      'scope',
      'request',
      'ai_verdict',
      'human_verdict',
      'ai_reasoning',
      'project_type',
    ])
    expect(record).not.toHaveProperty('accuracy')
  })

  it('emits null human_verdict for a debatable row', () => {
    const record = toEvaluationJsonlRecord({
      ...baseRow,
      aiVerdict: 'borderline',
      humanVerdict: null,
      industry: 'Design',
    })
    expect(record.ai_verdict).toBe('BORDERLINE')
    expect(record.human_verdict).toBeNull()
    expect(record.project_type).toBe('design')
  })

  it('maps Marketing to marketing', () => {
    const record = toEvaluationJsonlRecord({
      ...baseRow,
      industry: 'Marketing',
      aiVerdict: 'in_scope',
      humanVerdict: 'in_scope',
    })
    expect(record.ai_verdict).toBe('IN_SCOPE')
    expect(record.project_type).toBe('marketing')
  })
})

describe('serializeEvaluationJsonl', () => {
  it('returns an empty string for zero rows', () => {
    expect(serializeEvaluationJsonl([])).toBe('')
  })

  it('writes one compact object per line with a trailing newline', () => {
    const record = toEvaluationJsonlRecord({
      ...baseRow,
      humanVerdict: null,
    })
    const body = serializeEvaluationJsonl([record])
    expect(body).toBe(
      '{"scope":"Build a 5-page marketing site.","request":"Add 3 extra pages.","ai_verdict":"OUT_OF_SCOPE","human_verdict":null,"ai_reasoning":"Extra pages exceed the page limit.","project_type":"development"}\n',
    )
    const parsed = JSON.parse(body.trimEnd()) as Record<string, unknown>
    expect(Object.keys(parsed)).toEqual([
      'scope',
      'request',
      'ai_verdict',
      'human_verdict',
      'ai_reasoning',
      'project_type',
    ])
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
pnpm exec vitest run lib/evaluations/export.test.ts
```

Expected: FAIL — `Cannot find module './export'`.

- [ ] **Step 3: Write the implementation**

Create `lib/evaluations/export.ts`:

```ts
import type { Industry, Verdict } from '@/lib/types'

export type JsonlVerdict = 'IN_SCOPE' | 'BORDERLINE' | 'OUT_OF_SCOPE'
export type JsonlProjectType = 'development' | 'design' | 'marketing'

export interface EvaluationJsonlRecord {
  scope: string
  request: string
  ai_verdict: JsonlVerdict
  human_verdict: JsonlVerdict | null
  ai_reasoning: string
  project_type: JsonlProjectType
}

const VERDICT_JSONL: Record<Verdict, JsonlVerdict> = {
  in_scope: 'IN_SCOPE',
  borderline: 'BORDERLINE',
  out_of_scope: 'OUT_OF_SCOPE',
}

const INDUSTRY_JSONL: Record<Industry, JsonlProjectType> = {
  Development: 'development',
  Design: 'design',
  Marketing: 'marketing',
}

export function toEvaluationJsonlRecord(row: {
  scope: string
  request: string
  aiVerdict: Verdict
  humanVerdict: Verdict | null
  aiReasoning: string
  industry: Industry
}): EvaluationJsonlRecord {
  const human_verdict =
    row.humanVerdict === null ? null : VERDICT_JSONL[row.humanVerdict]
  return {
    scope: row.scope,
    request: row.request,
    ai_verdict: VERDICT_JSONL[row.aiVerdict],
    human_verdict,
    ai_reasoning: row.aiReasoning,
    project_type: INDUSTRY_JSONL[row.industry],
  }
}

export function serializeEvaluationJsonl(records: EvaluationJsonlRecord[]): string {
  if (records.length === 0) return ''
  return `${records.map((record) => JSON.stringify(record)).join('\n')}\n`
}
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
pnpm exec vitest run lib/evaluations/export.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add lib/evaluations/export.ts lib/evaluations/export.test.ts
git commit -m @"
Add JSONL mapping for evaluation snapshots.
"@
```

---

### Task 3: Postgres schema and migration

**Files:**
- Modify: `lib/db/schema.ts`
- Create (generated): `drizzle/0001_*.sql` and `drizzle/meta/*` (exact names come from drizzle-kit)

**Interfaces:**
- Consumes: existing `users`, `historyEntries`, `verdictEnum`, `industryEnum`
- Produces: `evaluationAccuracyEnum`; table `evaluationCases` with unique nullable `historyEntryId`, check constraint `evaluation_cases_accuracy_human_verdict`

- [ ] **Step 1: Extend `lib/db/schema.ts`**

Replace the file with:

```ts
import { sql } from 'drizzle-orm'
import {
  check,
  date,
  pgEnum,
  pgTable,
  text,
  timestamp,
  uuid,
} from 'drizzle-orm/pg-core'

export const industryEnum = pgEnum('industry', [
  'Development',
  'Design',
  'Marketing',
])

export const verdictEnum = pgEnum('verdict', [
  'in_scope',
  'borderline',
  'out_of_scope',
])

export const evaluationAccuracyEnum = pgEnum('evaluation_accuracy', [
  'correct',
  'wrong',
  'debatable',
])

export const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  email: text('email').notNull().unique(),
  passwordHash: text('password_hash').notNull(),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
})

export const projects = pgTable('projects', {
  id: uuid('id').primaryKey().defaultRandom(),
  userId: uuid('user_id')
    .notNull()
    .references(() => users.id, { onDelete: 'cascade' }),
  name: text('name').notNull(),
  client: text('client'),
  industry: industryEnum('industry').notNull(),
  scope: text('scope').notNull(),
  lastChecked: date('last_checked'),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
})

export const historyEntries = pgTable('history_entries', {
  id: uuid('id').primaryKey().defaultRandom(),
  projectId: uuid('project_id')
    .notNull()
    .references(() => projects.id, { onDelete: 'cascade' }),
  date: date('date').notNull(),
  request: text('request').notNull(),
  verdict: verdictEnum('verdict').notNull(),
  summary: text('summary').notNull(),
})

export const evaluationCases = pgTable(
  'evaluation_cases',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    userId: uuid('user_id')
      .notNull()
      .references(() => users.id, { onDelete: 'cascade' }),
    historyEntryId: uuid('history_entry_id')
      .unique()
      .references(() => historyEntries.id, { onDelete: 'set null' }),
    scope: text('scope').notNull(),
    request: text('request').notNull(),
    aiVerdict: verdictEnum('ai_verdict').notNull(),
    humanVerdict: verdictEnum('human_verdict'),
    aiReasoning: text('ai_reasoning').notNull(),
    accuracy: evaluationAccuracyEnum('accuracy').notNull(),
    industry: industryEnum('industry').notNull(),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    updatedAt: timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
  },
  (table) => [
    check(
      'evaluation_cases_accuracy_human_verdict',
      sql`(
        (${table.accuracy} = 'debatable' AND ${table.humanVerdict} IS NULL)
        OR
        (${table.accuracy} = 'correct' AND ${table.humanVerdict} IS NOT NULL AND ${table.humanVerdict} = ${table.aiVerdict})
        OR
        (${table.accuracy} = 'wrong' AND ${table.humanVerdict} IS NOT NULL AND ${table.humanVerdict} <> ${table.aiVerdict})
      )`,
    ),
  ],
)
```

- [ ] **Step 2: Generate and apply the migration**

```powershell
pnpm db:generate
pnpm db:up
pnpm db:migrate
```

Expected: drizzle-kit writes a new file under `drizzle/` that creates type `evaluation_accuracy`, table `evaluation_cases`, unique on `history_entry_id`, FKs (`user_id` cascade, `history_entry_id` set null), and check `evaluation_cases_accuracy_human_verdict`. `pnpm db:migrate` succeeds. Do not hand-edit generated SQL unless generate omitted the check — if omitted, add the check in schema (already there) and re-generate; do not invent a second table.

- [ ] **Step 3: Commit**

```powershell
git add lib/db/schema.ts drizzle
git commit -m @"
Add evaluation_cases table for labeled verdict snapshots.
"@
```

---

### Task 4: Data access and API routes

**Files:**
- Create: `lib/evaluations/data.ts`
- Create: `app/api/evaluations/route.ts`
- Create: `app/api/evaluations/export/route.ts`

**Interfaces:**
- Consumes: `parseEvaluationInput`, `resolveHumanVerdict`; `toEvaluationJsonlRecord`, `serializeEvaluationJsonl`; `evaluationCases`, `historyEntries`, `projects`; `getCurrentUser`; `readJsonObject`, `jsonError`
- Produces:
  - `export async function loadHistoryForUser(historyEntryId: string, userId: string): Promise<{ history: typeof historyEntries.$inferSelect; project: typeof projects.$inferSelect } | null>`
  - `export async function upsertEvaluationCase(input: EvaluationUpsertInput): Promise<{ id: string; accuracy: EvaluationAccuracy; humanVerdict: Verdict | null }>`
  - `export async function listEvaluationCasesForUser(userId: string): Promise<Array<{ scope: string; request: string; aiVerdict: Verdict; humanVerdict: Verdict | null; aiReasoning: string; industry: Industry }>>`
  - `POST /api/evaluations` → `200 { evaluation: { id, accuracy, humanVerdict } }`
  - `GET /api/evaluations/export` → JSONL attachment `scope-creep-evaluations.jsonl`

- [ ] **Step 1: Write `lib/evaluations/data.ts`**

```ts
import { and, asc, eq } from 'drizzle-orm'
import { db } from '@/lib/db'
import { evaluationCases, historyEntries, projects } from '@/lib/db/schema'
import type { EvaluationAccuracy, Industry, Verdict } from '@/lib/types'

export interface EvaluationUpsertInput {
  userId: string
  historyEntryId: string
  scope: string
  request: string
  aiVerdict: Verdict
  humanVerdict: Verdict | null
  aiReasoning: string
  accuracy: EvaluationAccuracy
  industry: Industry
}

export async function loadHistoryForUser(historyEntryId: string, userId: string) {
  const [row] = await db
    .select({
      history: historyEntries,
      project: projects,
    })
    .from(historyEntries)
    .innerJoin(projects, eq(historyEntries.projectId, projects.id))
    .where(and(eq(historyEntries.id, historyEntryId), eq(projects.userId, userId)))
    .limit(1)

  if (!row) return null
  return row
}

export async function upsertEvaluationCase(input: EvaluationUpsertInput) {
  const [row] = await db
    .insert(evaluationCases)
    .values({
      userId: input.userId,
      historyEntryId: input.historyEntryId,
      scope: input.scope,
      request: input.request,
      aiVerdict: input.aiVerdict,
      humanVerdict: input.humanVerdict,
      aiReasoning: input.aiReasoning,
      accuracy: input.accuracy,
      industry: input.industry,
    })
    .onConflictDoUpdate({
      target: evaluationCases.historyEntryId,
      set: {
        userId: input.userId,
        scope: input.scope,
        request: input.request,
        aiVerdict: input.aiVerdict,
        humanVerdict: input.humanVerdict,
        aiReasoning: input.aiReasoning,
        accuracy: input.accuracy,
        industry: input.industry,
        updatedAt: new Date(),
      },
    })
    .returning()

  if (!row) {
    console.error(
      JSON.stringify({
        event: 'evaluation_upsert_failed',
        userId: input.userId,
      }),
    )
    throw new Error('Evaluation case was not saved.')
  }

  return {
    id: row.id,
    accuracy: row.accuracy,
    humanVerdict: row.humanVerdict,
  }
}

export async function listEvaluationCasesForUser(userId: string) {
  return db
    .select({
      scope: evaluationCases.scope,
      request: evaluationCases.request,
      aiVerdict: evaluationCases.aiVerdict,
      humanVerdict: evaluationCases.humanVerdict,
      aiReasoning: evaluationCases.aiReasoning,
      industry: evaluationCases.industry,
    })
    .from(evaluationCases)
    .where(eq(evaluationCases.userId, userId))
    .orderBy(asc(evaluationCases.createdAt), asc(evaluationCases.id))
}
```

- [ ] **Step 2: Write `app/api/evaluations/route.ts`**

```ts
import { NextResponse } from 'next/server'
import { ERROR_CODES } from '@/lib/api/errors'
import { jsonError, readJsonObject } from '@/lib/api/json'
import { getCurrentUser } from '@/lib/auth/current-user'
import { loadHistoryForUser, upsertEvaluationCase } from '@/lib/evaluations/data'
import { parseEvaluationInput, resolveHumanVerdict } from '@/lib/evaluations/validation'

export async function POST(request: Request) {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)

  const body = await readJsonObject(request)
  if (!body) return jsonError(ERROR_CODES.requestBodyInvalid, 400)

  const parsed = parseEvaluationInput(body)
  if (!parsed.ok) return jsonError(parsed.error, parsed.status)

  const owned = await loadHistoryForUser(parsed.label.historyEntryId, user.id)
  if (!owned) return jsonError(ERROR_CODES.evaluationHistoryNotFound, 404)

  const resolved = resolveHumanVerdict(parsed.label, owned.history.verdict)
  if (!resolved.ok) return jsonError(resolved.error, 400)

  const evaluation = await upsertEvaluationCase({
    userId: user.id,
    historyEntryId: owned.history.id,
    scope: owned.project.scope,
    request: owned.history.request,
    aiVerdict: owned.history.verdict,
    humanVerdict: resolved.humanVerdict,
    aiReasoning: parsed.label.aiReasoning,
    accuracy: parsed.label.accuracy,
    industry: owned.project.industry,
  })

  return NextResponse.json({ evaluation }, { status: 200 })
}
```

- [ ] **Step 3: Write `app/api/evaluations/export/route.ts`**

```ts
import { NextResponse } from 'next/server'
import { ERROR_CODES } from '@/lib/api/errors'
import { jsonError } from '@/lib/api/json'
import { getCurrentUser } from '@/lib/auth/current-user'
import { listEvaluationCasesForUser } from '@/lib/evaluations/data'
import {
  serializeEvaluationJsonl,
  toEvaluationJsonlRecord,
} from '@/lib/evaluations/export'

export async function GET() {
  const user = await getCurrentUser()
  if (!user) return jsonError(ERROR_CODES.authRequired, 401)

  try {
    const rows = await listEvaluationCasesForUser(user.id)
    const body = serializeEvaluationJsonl(rows.map(toEvaluationJsonlRecord))
    return new NextResponse(body, {
      status: 200,
      headers: {
        'Content-Type': 'application/x-ndjson; charset=utf-8',
        'Content-Disposition': 'attachment; filename="scope-creep-evaluations.jsonl"',
      },
    })
  } catch (error) {
    console.error(
      JSON.stringify({
        event: 'evaluation_export_failed',
        userId: user.id,
        message: error instanceof Error ? error.message : 'unknown',
      }),
    )
    throw error
  }
}
```

- [ ] **Step 4: Typecheck routes**

```powershell
pnpm exec tsc --noEmit
```

Expected: PASS. If `humanVerdict` type from drizzle is `Verdict | null` vs `string | null`, do not coerce with `as` fallbacks; fix the schema/return type so it is `Verdict | null`.

- [ ] **Step 5: Commit**

```powershell
git add lib/evaluations/data.ts app/api/evaluations/route.ts app/api/evaluations/export/route.ts
git commit -m @"
Add evaluation upsert and per-user JSONL export APIs.
"@
```

---

### Task 5: i18n strings and store wiring

**Files:**
- Modify: `messages/en.json`
- Modify: `messages/ru.json`
- Modify: `components/scope-guard/store.tsx`

**Interfaces:**
- Consumes: `POST /api/evaluations`, `GET /api/evaluations/export`, `HistoryResponse.entry.id`, `result.reasoning`
- Produces:
  - Store fields: `currentHistoryEntryId: string | null`
  - `submitEvaluation(input: { accuracy: EvaluationAccuracy; humanVerdict?: Verdict }): Promise<void>`
  - `downloadEvaluationsExport(): Promise<void>`
  - Message keys under `feedback.*`, `history.downloadEvaluations`, `history.downloadingEvaluations`, and the three `errors.evaluation*` keys

- [ ] **Step 1: Add EN/RU strings**

In `messages/en.json`:

1. Inside `"history"`, add after `"emptyDescription"`:

```json
    "downloadEvaluations": "Download evaluation JSONL",
    "downloadingEvaluations": "Downloading..."
```

2. Add a sibling of `"result"` named `"feedback"`:

```json
  "feedback": {
    "heading": "Was this verdict correct?",
    "correct": "Correct",
    "wrong": "Wrong",
    "debatable": "Debatable",
    "expectedHeading": "What should it have been?",
    "saved": "Saved",
    "change": "Change"
  },
```

3. Inside `"errors"`, add:

```json
    "evaluationReasoningRequired": "Model reasoning is required.",
    "evaluationLabelInvalid": "That verdict label is invalid.",
    "evaluationHistoryNotFound": "That scope check was not found."
```

In `messages/ru.json`, same locations:

```json
    "downloadEvaluations": "Скачать evaluation JSONL",
    "downloadingEvaluations": "Скачивание..."
```

```json
  "feedback": {
    "heading": "Этот вердикт верный?",
    "correct": "Верно",
    "wrong": "Неверно",
    "debatable": "Спорно",
    "expectedHeading": "Каким он должен был быть?",
    "saved": "Сохранено",
    "change": "Изменить"
  },
```

```json
    "evaluationReasoningRequired": "Нужен reasoning модели.",
    "evaluationLabelInvalid": "Некорректная оценка вердикта.",
    "evaluationHistoryNotFound": "Запись проверки не найдена."
```

Keep JSON valid (commas). Do not translate user-entered scope/request/reasoning.

- [ ] **Step 2: Wire the store**

In `components/scope-guard/store.tsx`:

1. Import `EvaluationAccuracy` and `Verdict` (Verdict may already be unused — import what is needed):

```ts
import type {
  AnalysisResult,
  EvaluationAccuracy,
  HistoryEntry,
  Industry,
  Project,
  Verdict,
} from '@/lib/types'
```

2. Add to `StoreValue`:

```ts
  currentHistoryEntryId: string | null
  submitEvaluation: (input: {
    accuracy: EvaluationAccuracy
    humanVerdict?: Verdict
  }) => Promise<void>
  downloadEvaluationsExport: () => Promise<void>
```

3. State next to `result`:

```ts
  const [currentHistoryEntryId, setCurrentHistoryEntryId] = useState<string | null>(
    null,
  )
```

4. Change `persistHistory` so it returns the created entry:

```ts
  async function persistHistory(projectId: string, entry: Omit<HistoryEntry, 'id'>) {
    const data = await apiFetch<HistoryResponse>(
      `/api/projects/${projectId}/history`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(entry),
      },
    )

    applyHistory(projectId, data.entry)
    return data.entry
  }
```

5. In `selectProject`, after `setResult(null)` add `setCurrentHistoryEntryId(null)`.

6. In `createProject`, after `setResult(null)` add `setCurrentHistoryEntryId(null)`.

7. In `loadExample`, after `setResult(null)` add `setCurrentHistoryEntryId(null)`.

8. In `reset`, after `setResult(null)` add `setCurrentHistoryEntryId(null)`.

9. In `runCheck`, when setting loading, also `setCurrentHistoryEntryId(null)`.

10. In `runAnalysis`, after a successful analyze, use the returned history id:

```ts
      const analysis = data.result
      const historyEntry = await persistHistory(project.id, {
        date: todayISO(),
        request,
        verdict: analysis.verdict,
        summary: analysis.summary,
      })
      setCurrentHistoryEntryId(historyEntry.id)
      setResult(analysis)
      setStatus('result')
```

11. Add these functions before `const value`:

```ts
  async function submitEvaluation(input: {
    accuracy: EvaluationAccuracy
    humanVerdict?: Verdict
  }) {
    if (!currentHistoryEntryId) {
      throw new Error('currentHistoryEntryId is required')
    }
    if (!result) {
      throw new Error('result is required')
    }
    if (input.accuracy === 'wrong' && !input.humanVerdict) {
      throw new Error('humanVerdict is required')
    }

    const body: Record<string, unknown> = {
      historyEntryId: currentHistoryEntryId,
      accuracy: input.accuracy,
      aiReasoning: result.reasoning,
    }
    if (input.accuracy === 'wrong') {
      body.humanVerdict = input.humanVerdict
    }

    try {
      await apiFetch<{ evaluation: { id: string } }>('/api/evaluations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'evaluation_submit_failed',
          message: error instanceof Error ? error.message : 'Unknown evaluation error',
          status: error instanceof ApiError ? error.status : null,
        }),
      )
      if (error instanceof ApiError && error.status === 401) {
        router.replace('/login')
      }
      throw error
    }
  }

  async function downloadEvaluationsExport() {
    let response: Response
    try {
      response = await fetch('/api/evaluations/export')
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'evaluation_export_request_failed',
          message: error instanceof Error ? error.message : 'Unknown export error',
        }),
      )
      throw new ApiError(ERROR_CODES.requestFailed, 0)
    }

    if (response.status === 401) {
      router.replace('/login')
      throw new ApiError(ERROR_CODES.authRequired, 401)
    }

    if (!response.ok) {
      console.error(
        JSON.stringify({
          event: 'evaluation_export_http_failed',
          status: response.status,
        }),
      )
      throw new ApiError(ERROR_CODES.requestFailed, response.status)
    }

    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'scope-creep-evaluations.jsonl'
    link.click()
    URL.revokeObjectURL(url)
  }
```

12. Put `currentHistoryEntryId`, `submitEvaluation`, and `downloadEvaluationsExport` on `value`.

`submitEvaluation` must omit `humanVerdict` for correct/debatable. Do not send scope, request, or AI verdict from the client as authoritative fields.

- [ ] **Step 3: Typecheck**

```powershell
pnpm exec tsc --noEmit
```

Expected: PASS. Store is unused by UI yet; that is OK if `StoreValue` is satisfied.

- [ ] **Step 4: Commit**

```powershell
git add messages/en.json messages/ru.json components/scope-guard/store.tsx
git commit -m @"
Wire evaluation submit and JSONL download into the workspace store.
"@
```

---

### Task 6: Result-panel feedback card

**Files:**
- Create: `components/scope-guard/verdict-feedback.tsx`
- Modify: `components/scope-guard/result-panel.tsx`

**Interfaces:**
- Consumes: `useStore().currentHistoryEntryId`, `submitEvaluation`; `feedback.*` and `verdict.*` messages; `Verdict` radios
- Produces: card after Why section, before verify warning; Correct/Debatable POST on click; Wrong POST when expected verdict chosen; Change resets local UI

- [ ] **Step 1: Create `components/scope-guard/verdict-feedback.tsx`**

```tsx
'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { assertErrorCode, type ErrorCode } from '@/lib/api/errors'
import type { EvaluationAccuracy, Verdict } from '@/lib/types'
import { cn } from '@/lib/utils'
import { useStore } from './store'

const ACCURACY_ORDER: EvaluationAccuracy[] = ['correct', 'wrong', 'debatable']
const VERDICT_ORDER: Verdict[] = ['in_scope', 'borderline', 'out_of_scope']

const accuracyStyles: Record<EvaluationAccuracy, string> = {
  correct:
    'border-inscope-border bg-inscope-soft text-inscope-text aria-pressed:ring-2 aria-pressed:ring-inscope',
  wrong:
    'border-outscope-border bg-outscope-soft text-outscope-text aria-pressed:ring-2 aria-pressed:ring-outscope',
  debatable:
    'border-borderline-border bg-borderline-soft text-borderline-text aria-pressed:ring-2 aria-pressed:ring-borderline',
}

const accuracyPrefix: Record<EvaluationAccuracy, string> = {
  correct: '👍',
  wrong: '👎',
  debatable: '🤔',
}

export function VerdictFeedback() {
  const { currentHistoryEntryId, submitEvaluation } = useStore()
  const t = useTranslations()
  const [accuracy, setAccuracy] = useState<EvaluationAccuracy | null>(null)
  const [expectedVerdict, setExpectedVerdict] = useState<Verdict | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isSaved, setIsSaved] = useState(false)
  const [saveError, setSaveError] = useState<ErrorCode | ''>('')

  if (!currentHistoryEntryId) return null

  async function save(nextAccuracy: EvaluationAccuracy, nextExpected: Verdict | null) {
    if (nextAccuracy === 'wrong' && !nextExpected) {
      throw new Error('humanVerdict is required')
    }
    setIsSaving(true)
    setSaveError('')
    try {
      await submitEvaluation(
        nextAccuracy === 'wrong'
          ? { accuracy: 'wrong', humanVerdict: nextExpected }
          : { accuracy: nextAccuracy },
      )
      setIsSaved(true)
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'verdict_feedback_save_failed',
          message: error instanceof Error ? error.message : 'Unknown save error',
        }),
      )
      if (!(error instanceof Error)) {
        throw new Error('Unknown save error')
      }
      setSaveError(assertErrorCode(error.message))
    } finally {
      setIsSaving(false)
    }
  }

  async function onAccuracyClick(next: EvaluationAccuracy) {
    if (isSaving) return
    setAccuracy(next)
    setExpectedVerdict(null)
    setIsSaved(false)
    if (next === 'wrong') return
    await save(next, null)
  }

  async function onExpectedChange(next: Verdict) {
    if (isSaving || accuracy !== 'wrong') return
    setExpectedVerdict(next)
    setIsSaved(false)
    await save('wrong', next)
  }

  function onChange() {
    setAccuracy(null)
    setExpectedVerdict(null)
    setIsSaved(false)
    setSaveError('')
  }

  if (isSaved) {
    if (!accuracy) {
      throw new Error('accuracy is required after save')
    }
    if (accuracy === 'wrong' && !expectedVerdict) {
      throw new Error('expectedVerdict is required after wrong save')
    }
    const savedLabel =
      accuracy === 'wrong'
        ? `${t('feedback.wrong')} → ${t(`verdict.${expectedVerdict}`)}`
        : t(`feedback.${accuracy}`)

    return (
      <section
        aria-labelledby="feedback-heading"
        className="rounded-lg border border-border bg-card p-4"
      >
        <h3 id="feedback-heading" className="text-sm font-semibold text-foreground">
          {t('feedback.heading')}
        </h3>
        <p className="mt-2 text-sm text-foreground/80">
          {t('feedback.saved')}: {savedLabel}
        </p>
        <Button
          type="button"
          variant="link"
          className="mt-1 h-auto px-0"
          onClick={onChange}
        >
          {t('feedback.change')}
        </Button>
      </section>
    )
  }

  return (
    <section
      aria-labelledby="feedback-heading"
      className="rounded-lg border border-border bg-card p-4"
    >
      <h3 id="feedback-heading" className="text-sm font-semibold text-foreground">
        {t('feedback.heading')}
      </h3>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        {ACCURACY_ORDER.map((value) => (
          <Button
            key={value}
            type="button"
            variant="outline"
            disabled={isSaving}
            aria-pressed={accuracy === value}
            className={cn('h-9 justify-center', accuracyStyles[value])}
            onClick={() => {
              void onAccuracyClick(value)
            }}
          >
            <span aria-hidden="true">{accuracyPrefix[value]}</span>
            {t(`feedback.${value}`)}
          </Button>
        ))}
      </div>

      {accuracy === 'wrong' ? (
        <fieldset className="mt-4" disabled={isSaving}>
          <legend className="text-sm font-medium text-foreground">
            {t('feedback.expectedHeading')}
          </legend>
          <div className="mt-2 flex flex-col gap-2" role="radiogroup">
            {VERDICT_ORDER.map((value) => (
              <label
                key={value}
                className="flex items-center gap-2 text-sm text-foreground"
              >
                <input
                  type="radio"
                  name="expected-verdict"
                  value={value}
                  checked={expectedVerdict === value}
                  onChange={() => {
                    void onExpectedChange(value)
                  }}
                />
                {t(`verdict.${value}`)}
              </label>
            ))}
          </div>
        </fieldset>
      ) : null}

      {saveError ? (
        <p className="mt-3 text-sm text-outscope-text" role="alert">
          {t(saveError)}
        </p>
      ) : null}
    </section>
  )
}
```

If `accuracy === 'wrong'` in the saved branch, `expectedVerdict` is required (it was chosen before POST). Do not substitute a placeholder label.

- [ ] **Step 2: Mount the card in `result-panel.tsx`**

Add import:

```ts
import { VerdictFeedback } from './verdict-feedback'
```

In `ResultState`, after the Why `</section>` and **before** the verify-warning `<p>`, insert:

```tsx
      <VerdictFeedback key={currentHistoryEntryId ?? 'unlabeled'} />
```

`ResultState` already reads `result` and `selectedProject` from `useStore()`. Also read `currentHistoryEntryId` from `useStore()` for the `key`.

- [ ] **Step 3: Lint and typecheck**

```powershell
pnpm exec tsc --noEmit
pnpm lint
```

Expected: PASS. Fix unused imports if ESLint reports them.

- [ ] **Step 4: Commit**

```powershell
git add components/scope-guard/verdict-feedback.tsx components/scope-guard/result-panel.tsx
git commit -m @"
Add verdict accuracy feedback on the result panel.
"@
```

---

### Task 7: History JSONL download

**Files:**
- Modify: `components/scope-guard/history-view.tsx`

**Interfaces:**
- Consumes: `downloadEvaluationsExport` from the store; `history.downloadEvaluations`
- Produces: button next to the History title; `401` → login; other failures → `errors.requestFailed`

- [ ] **Step 1: Update `HistoryView`**

Replace `components/scope-guard/history-view.tsx` with:

```tsx
'use client'

import { useState } from 'react'
import { Clock } from 'lucide-react'
import { useLocale, useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { assertErrorCode, type ErrorCode } from '@/lib/api/errors'
import { localeToDateLocale, type Locale } from '@/i18n/config'
import { VerdictChip } from './verdict'
import { useStore } from './store'

function formatDate(iso: string, locale: Locale) {
  return new Date(iso).toLocaleDateString(localeToDateLocale(locale), {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function HistoryView() {
  const { selectedProject, downloadEvaluationsExport } = useStore()
  const locale = useLocale()
  const t = useTranslations()
  const [isDownloading, setIsDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<ErrorCode | ''>('')

  if (!selectedProject) {
    return (
      <div className="mx-auto max-w-2xl text-center text-sm text-muted-foreground">
        {t('history.selectProject')}
      </div>
    )
  }

  const { history } = selectedProject

  async function onDownload() {
    setIsDownloading(true)
    setDownloadError('')
    try {
      await downloadEvaluationsExport()
    } catch (error) {
      console.error(
        JSON.stringify({
          event: 'evaluation_download_failed',
          message: error instanceof Error ? error.message : 'Unknown download error',
        }),
      )
      if (!(error instanceof Error)) {
        throw new Error('Unknown download error')
      }
      setDownloadError(assertErrorCode(error.message))
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-foreground">
            {t('history.title')}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {t('history.previousChecks', {
              projectName: selectedProject.name,
            })}
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          className="h-9"
          disabled={isDownloading}
          onClick={() => {
            void onDownload()
          }}
        >
          {isDownloading
            ? t('history.downloadingEvaluations')
            : t('history.downloadEvaluations')}
        </Button>
      </div>
      {downloadError ? (
        <p className="mt-3 text-sm text-outscope-text" role="alert">
          {t(downloadError)}
        </p>
      ) : null}

      {history.length === 0 ? (
        <div className="mt-6 rounded-xl border border-dashed border-border bg-card/50 p-10 text-center">
          <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-muted">
            <Clock className="size-6 text-muted-foreground" aria-hidden="true" />
          </span>
          <h3 className="mt-4 text-base font-semibold text-foreground">
            {t('history.emptyTitle')}
          </h3>
          <p className="mx-auto mt-1.5 max-w-sm text-sm text-muted-foreground text-pretty">
            {t('history.emptyDescription')}
          </p>
        </div>
      ) : (
        <ul className="mt-6 flex flex-col gap-3">
          {history.map((h) => (
            <li
              key={h.id}
              className="rounded-lg border border-border bg-card p-4"
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-xs text-muted-foreground">
                  {formatDate(h.date, locale)}
                </span>
                <VerdictChip verdict={h.verdict} />
              </div>
              <p className="mt-2 text-sm leading-relaxed text-foreground text-pretty">
                {h.request}
              </p>
              <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground text-pretty">
                {h.summary}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
```

The download button stays visible when history is empty (export can still be empty or contain cases from other projects). Do not add labeling controls on history cards.

- [ ] **Step 2: Typecheck and lint**

```powershell
pnpm exec tsc --noEmit
pnpm lint
```

Expected: PASS.

- [ ] **Step 3: Commit**

```powershell
git add components/scope-guard/history-view.tsx
git commit -m @"
Add per-user evaluation JSONL download on History.
"@
```

---

### Task 8: Docs, regression, HTTP smoke

**Files:**
- Modify: `docs/status.md`
- Modify: `docs/plans.md`
- Modify: `docs/test-plan.md`

**Interfaces:**
- Consumes: completed Tasks 1–7
- Produces: documented slice + passing `pnpm test` / lint / tsc / build; optional live HTTP smoke

- [ ] **Step 1: Update docs**

In `docs/status.md`:

- Current Phase: mention verdict labeling + JSONL export exist on the Check-scope result / History.
- Done: add a bullet that signed-in users can mark Correct / Wrong / Debatable, upsert `evaluation_cases`, and download only their JSONL (`scope`, `request`, `ai_verdict`, `human_verdict`, `ai_reasoning`, `project_type`).
- Decisions: evaluation rows are per-user; Debatable stores `human_verdict` null; unlabeled checks are not inserted.

In `docs/plans.md`, append:

```markdown
# Verdict Evaluation Dataset

## Goal

Collect human labels on AI verdicts for an internal evaluation JSONL dataset.

## Milestones

### 1. Label + persist

- Result-panel Correct / Wrong / Debatable (Wrong asks for the expected verdict).
- Postgres `evaluation_cases` snapshot upserted on `history_entry_id`.

### 2. Export

- `GET /api/evaluations/export` JSONL for the current user only.

Definition of done: a user can label a fresh verdict, change the label, and download only their cases in the six-field JSONL contract; User B cannot read User A's cases.

Validation:

- `pnpm test`
- `pnpm lint`
- `pnpm exec tsc --noEmit`
- `pnpm db:migrate`
```

In `docs/test-plan.md`, append:

```markdown
# Verdict Evaluation Dataset Test Plan

## Critical Paths

- After Check scope, the result panel shows Was this verdict correct? with Correct / Wrong / Debatable.
- Correct and Debatable save immediately; Wrong asks What should it have been? then saves.
- Change allows a new label; the same history id upserts one row.
- History Download evaluation JSONL downloads `scope-creep-evaluations.jsonl` for the signed-in user (all their projects).
- JSONL keys are exactly scope, request, ai_verdict, human_verdict, ai_reasoning, project_type; Debatable has human_verdict null.
- User B cannot POST User A's historyEntryId (`404 errors.evaluationHistoryNotFound`).
- Unauthenticated POST /api/evaluations and GET /api/evaluations/export return `401`.

## Commands

- `pnpm test`
- `pnpm lint`
- `pnpm exec tsc --noEmit`
- `pnpm build`
- `pnpm db:migrate`

## Release Gate

The feature is ready when a labeled Check scope produces a snapshot row, JSONL matches the locked contract, and evaluation data is isolated by `user_id`.
```

- [ ] **Step 2: Full verification**

```powershell
pnpm test
pnpm lint
pnpm exec tsc --noEmit
pnpm build
```

Expected: all succeed. Next.js may still report the existing middleware-to-proxy deprecation; that is not a failure of this slice.

HTTP smoke (PowerShell `Invoke-WebRequest`, session cookie, local Postgres migrated). Do not claim this passed if it was not run:

1. No cookie: `POST /api/evaluations` and `GET /api/evaluations/export` → `401`.
2. Owner with a real `historyEntryId` and `aiReasoning`: POST `accuracy=correct` → `200`; POST `accuracy=wrong` + different `humanVerdict` on the same id → `200`.
3. User B POST User A's `historyEntryId` → `404` `errors.evaluationHistoryNotFound`.
4. Wrong without `humanVerdict` → `400` `errors.evaluationLabelInvalid`.
5. Owner export: each non-empty line is JSON with the six keys; User B export does not contain User A's `request`/`scope` strings.

- [ ] **Step 3: Commit**

```powershell
git add docs/status.md docs/plans.md docs/test-plan.md
git commit -m @"
Document verdict evaluation labeling and JSONL export.
"@
```

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|---|---|
| Result-panel Correct / Wrong / Debatable | Task 6 |
| Wrong → expected In/Borderline/Out; Debatable no expected verdict | Tasks 1, 6 |
| Correct `human_verdict` = AI; Debatable null | Tasks 1, 4 |
| Separate `evaluation_cases` + unique history id upsert | Tasks 3, 4 |
| Snapshot scope/industry at label time; request/verdict from history; reasoning from body | Task 4 |
| Per-user isolation; User B 404 / export filter | Tasks 4, 8 |
| JSONL six fields, casing, empty file 200 | Tasks 2, 4, 7 |
| `accuracy` DB-only | Tasks 2, 3 |
| History delete SET NULL; user delete CASCADE | Task 3 |
| POST 200; no 201 split | Task 4 |
| No History-card labeling; export button on History | Task 7 |
| EN/RU copy + error keys | Task 5 |
| No dashboard / prompt change / retries / defaults | All tasks omit these |
| Unit tests for parse + JSONL mapping | Tasks 1–2 |
| `pnpm db:generate` / migrate / test / lint / tsc / build | Tasks 3, 8 |
| `currentHistoryEntryId` after persistHistory | Task 5 |
| Logs without scope/request/reasoning | Tasks 4, 5, 6, 7 |
