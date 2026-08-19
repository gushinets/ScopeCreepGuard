# Design: Verdict Evaluation Dataset (Internal MVP)

Date: 2026-08-19  
Source: internal MVP goal — measure verdict accuracy via human labels; produce a real evaluation dataset from the first 50–100 cases  
Slice: Collect labels on a fresh Check scope result, persist per-user snapshots, export JSONL. No accuracy dashboard.

## Goal

After each AI verdict, a signed-in user can mark it **Correct**, **Wrong**, or **Debatable**. Wrong requires the verdict it should have been. Each labeled check becomes one frozen evaluation case. The user can download their cases as JSONL. That file is the asset for later analysis (over/under-estimate, borderline frequency, industry differences, prompt v2 rules). This slice does not analyze the dataset in-product.

## Decisions (locked)

| Topic | Choice |
|---|---|
| Product slice | Collection only: result-panel labeling + per-user JSONL export |
| Storage | New Postgres table `evaluation_cases` (not a disk JSONL log, not extra columns on `history_entries`) |
| Isolation | A user labels and exports only their own cases |
| Labeling surface | Fresh result panel only. No labeling from History list |
| Debatable | Do not ask for an expected verdict. `human_verdict` is JSON `null` |
| Correct | Server sets `human_verdict` equal to `ai_verdict`. Client must not send `humanVerdict` |
| Wrong | Client must send a different expected verdict. Same-as-AI is invalid |
| Submit UX | Correct / Debatable save on click. Wrong saves when the expected verdict is chosen. No extra Submit button |
| One check, one row | Unique `history_entry_id`. Repeat submit upserts (misclick / Change) |
| Unlabeled checks | Not inserted. Table contains only submitted labels |
| JSONL fields | Exactly `scope`, `request`, `ai_verdict`, `human_verdict`, `ai_reasoning`, `project_type` |
| `accuracy` | Stored in DB only. Not written to JSONL (Correct / Wrong / Debatable are recoverable from `human_verdict` vs `ai_verdict`) |
| Export verdict casing | `IN_SCOPE` / `BORDERLINE` / `OUT_OF_SCOPE` |
| Export project type | `development` / `design` / `marketing` (from snapshot `Development` / `Design` / `Marketing`) |
| Snapshot timing | Scope and industry from the project at label upsert time; request and AI verdict from the history row; reasoning from the client body (`result.reasoning`) |
| History delete | `history_entry_id` `ON DELETE SET NULL`. Labeled snapshots remain |
| User delete | `user_id` `ON DELETE CASCADE` |
| Empty export | HTTP `200` and a zero-byte JSONL file |
| Fallback / retries | None |

## Out of this slice

- Accuracy dashboard, confusion matrix, filters, per-industry charts
- Labeling or relabeling from History cards
- Cross-user / team-wide export
- Changing the classification prompt or model
- Storing full `AnalysisResult` (replies, change order, citations, confidence) on the evaluation row
- Client-supplied `ai_verdict`, `request`, `scope`, or `industry` as source of truth

## Architecture

Keep Next.js App Router + Postgres + session cookies.

Check scope is unchanged until the result is on screen:

1. User runs Check scope → `POST /api/analyze` → client `POST /api/projects/:id/history`.
2. Store keeps `currentHistoryEntryId` from the created history row together with `result`.
3. Result panel shows the existing verdict / why block, then the new feedback card.
4. Completed label → `POST /api/evaluations` → upsert `evaluation_cases` for that user.
5. History view → `GET /api/evaluations/export` → download that user’s JSONL.

```
[Check Scope]
  POST /api/analyze → result
  POST /api/projects/:id/history → history.id
  result panel + feedback card
    POST /api/evaluations
      session user
      history JOIN project WHERE project.user_id = user
      snapshot + accuracy rules
      upsert on history_entry_id
  History: GET /api/evaluations/export → JSONL (WHERE user_id = user)
```

## Data model

Table `evaluation_cases`:

| Column | Type | Rules |
|---|---|---|
| `id` | uuid PK | default random |
| `user_id` | uuid | not null, FK `users(id)` `ON DELETE CASCADE` |
| `history_entry_id` | uuid | unique, nullable, FK `history_entries(id)` `ON DELETE SET NULL` |
| `scope` | text | not null, snapshot |
| `request` | text | not null, from history |
| `ai_verdict` | existing `verdict` enum | not null, from history |
| `human_verdict` | existing `verdict` enum | nullable |
| `ai_reasoning` | text | not null, trimmed client `result.reasoning` |
| `accuracy` | new enum `evaluation_accuracy`: `correct`, `wrong`, `debatable` | not null |
| `industry` | existing `industry` enum | not null, snapshot |
| `created_at` | timestamptz | default now |
| `updated_at` | timestamptz | default now; set on upsert |

Check constraints (fail at DB if application validation is skipped):

- `debatable` → `human_verdict` IS NULL
- `correct` → `human_verdict` IS NOT NULL AND `human_verdict` = `ai_verdict`
- `wrong` → `human_verdict` IS NOT NULL AND `human_verdict` <> `ai_verdict`

Drizzle schema + generated migration. No silent default accuracy or verdict.

## API

### `POST /api/evaluations`

Session required.

Request body:

```json
{
  "historyEntryId": "<uuid>",
  "accuracy": "correct" | "wrong" | "debatable",
  "humanVerdict": "in_scope" | "borderline" | "out_of_scope",
  "aiReasoning": "<non-empty string>"
}
```

`humanVerdict` is required for `wrong` and forbidden for `correct` and `debatable` (omit the key; do not send `null` as a substitute for omit — parser rejects `humanVerdict` present unless `accuracy` is `wrong`).

Server steps:

1. Parse JSON object; malformed → `400 errors.requestBodyInvalid`.
2. Validate `historyEntryId` as uuid, `accuracy`, `aiReasoning` (trim, non-empty), and `humanVerdict` combination. Invalid uuid → `404 errors.evaluationHistoryNotFound` (same class as missing/foreign history; do not leak existence).
3. Load history joined to project where `projects.user_id` is the current user. Missing or foreign → `404 errors.evaluationHistoryNotFound`.
4. Derive `human_verdict`: `wrong` → body `humanVerdict` (must differ from `history.verdict`); `correct` → `history.verdict`; `debatable` → `null`.
5. Upsert on `history_entry_id`: set `user_id`, `scope` = `project.scope`, `request` = `history.request`, `ai_verdict` = `history.verdict`, `ai_reasoning` = trimmed body, `accuracy`, `human_verdict`, `industry` = `project.industry`, `updated_at` = now. Insert sets `created_at`.
6. If returning row is missing → log `evaluation_upsert_failed` with `userId` and throw (same fail-fast pattern as history insert).

Success is always `200` (insert and update share one upsert; do not distinguish 201):

```json
{
  "evaluation": {
    "id": "<uuid>",
    "accuracy": "wrong",
    "humanVerdict": "in_scope"
  }
}
```

For `debatable`, `humanVerdict` is JSON `null`. For `correct`, `humanVerdict` equals the history AI verdict.

### `GET /api/evaluations/export`

Session required. Query `evaluation_cases` where `user_id` = current user, order `created_at` ascending, `id` ascending as tie-breaker.

Response:

- `200`
- `Content-Type: application/x-ndjson; charset=utf-8`
- `Content-Disposition: attachment; filename="scope-creep-evaluations.jsonl"`
- One compact JSON object per line; UTF-8; newline after each object including the last. Zero rows → empty body.

Each line (and only these keys, this order):

```json
{
  "scope": "...",
  "request": "...",
  "ai_verdict": "OUT_OF_SCOPE",
  "human_verdict": "IN_SCOPE",
  "ai_reasoning": "...",
  "project_type": "development"
}
```

Debatable line uses `"human_verdict": null`.

Mapping:

| DB | JSONL |
|---|---|
| `in_scope` | `IN_SCOPE` |
| `borderline` | `BORDERLINE` |
| `out_of_scope` | `OUT_OF_SCOPE` |
| `Development` | `development` |
| `Design` | `design` |
| `Marketing` | `marketing` |

Do not include `accuracy`, ids, timestamps, or other users’ rows.

## UI

### Result panel feedback card

Place after the “Why this verdict” section (reasoning, citations, suggestion) and before the verify warning, Client reply, and Change Order.

Copy (EN / RU via `next-intl`):

- Heading: Was this verdict correct?
- 👍 Correct
- 👎 Wrong
- 🤔 Debatable
- Follow-up heading (Wrong only): What should it have been?
- Radios: In scope / Borderline / Out of scope (reuse existing verdict label keys)
- Saved confirmation
- Change (resets the card; next complete selection upserts)

Visual: existing card/border. Correct uses in-scope colors; Wrong uses out-of-scope; Debatable uses borderline. Three choice buttons in a row, column on small screens.

Behavior:

- Choosing Correct or Debatable immediately `POST`s.
- Choosing Wrong reveals the expected-verdict radios and does not POST until a radio is selected.
- While the request is in flight, disable the controls.
- Success: show saved state for that `currentHistoryEntryId`. Change returns to the empty card (previous server row remains until a new complete selection).
- API error: show the translated error key; keep the current selection so the user can retry.
- New Check scope result (new history id) resets the card to unlabeled.

Store: after `persistHistory`, keep `currentHistoryEntryId` with the in-memory result. POST body `aiReasoning` is `result.reasoning`. Do not send scope, request, or AI verdict from the client as authoritative fields.

### History export

On History, next to the title: **Download evaluation JSONL**. Always visible when a project is selected. Click → `GET /api/evaluations/export` → browser download of the user’s full dataset (all their projects), not only the selected project. Empty dataset downloads an empty file. `401` follows the existing store redirect to login. Any other failed export → show `errors.requestFailed` on History (response body is a file, not `{ error }`).

No feedback controls on History cards.

## Components

| Module | Responsibility |
|---|---|
| `lib/db/schema.ts` | `evaluation_accuracy` enum; `evaluation_cases` table; check constraints |
| `drizzle/` | Generated migration |
| `lib/evaluations/validation.ts` | Parse POST body; fail-fast error codes; no defaults |
| `lib/evaluations/export.ts` | Map a DB row to the six-field JSONL object |
| `lib/evaluations/data.ts` | Load owned history+project; upsert; list rows for export |
| `app/api/evaluations/route.ts` | `POST` create/update |
| `app/api/evaluations/export/route.ts` | `GET` JSONL |
| `lib/api/errors.ts` | New error codes |
| `lib/types.ts` | `EvaluationAccuracy`; POST/response types as needed |
| `components/scope-guard/verdict-feedback.tsx` | Feedback card |
| `components/scope-guard/result-panel.tsx` | Mount card in ResultState |
| `components/scope-guard/store.tsx` | `currentHistoryEntryId`; submit evaluation |
| `components/scope-guard/history-view.tsx` | Export button |
| `messages/en.json`, `messages/ru.json` | Feedback, export, and error strings |
| `middleware.ts` | No change: existing `/api/*` session gate already covers the new routes |

Analyze, prompt, history schema contract, and verdict banner stay unchanged except for the new card and `currentHistoryEntryId`.

## Error handling

| Situation | HTTP | Key |
|---|---|---|
| No session | 401 | `errors.authRequired` |
| Body not a JSON object | 400 | `errors.requestBodyInvalid` |
| Empty / missing `aiReasoning` | 400 | `errors.evaluationReasoningRequired` |
| Invalid `accuracy`; `humanVerdict` present when not `wrong`; `humanVerdict` missing/invalid when `wrong`; expected verdict equals AI verdict | 400 | `errors.evaluationLabelInvalid` |
| Invalid uuid, missing history, or history whose project is not owned by the user | 404 | `errors.evaluationHistoryNotFound` |
| Upsert returns no row | throw after log `evaluation_upsert_failed` | same pattern as missing history insert |
| Export query failure | log `evaluation_export_failed` with `userId`, rethrow | do not return a partial file |
| Export with zero rows | 200 empty body | not an error |

Logs are JSON with `event` and `userId`. Do not log `scope`, `request`, or `ai_reasoning`.

No retries. No chained defaults (`a or b or c`) for required fields. No inventing `human_verdict` on Debatable.

Client: `401` → login redirect (existing store behavior). Other errors → translated message on the card. Export download failure → translated error on History.

## Testing

Unit:

- `lib/evaluations/validation.ts`: Correct without `humanVerdict` ok; Debatable without `humanVerdict` ok; Wrong requires a different verdict; Wrong with same-as-AI rejected; Correct/Debatable with `humanVerdict` rejected; empty reasoning rejected; invalid accuracy rejected.
- `lib/evaluations/export.ts`: `out_of_scope` → `OUT_OF_SCOPE`; `Development` → `development`; Debatable row emits `human_verdict: null`; output keys are exactly the six specified, in order; `accuracy` absent.

HTTP smoke (PowerShell `Invoke-WebRequest`, session cookie):

- `POST /api/evaluations` and `GET /api/evaluations/export` without cookie → `401`.
- Owner: Check scope (or existing history id) → POST Correct `200` → POST Wrong on same id `200` and row updated.
- User B POST with User A’s `historyEntryId` → `404`.
- User B export does not contain User A’s cases.
- Wrong without `humanVerdict` → `400 errors.evaluationLabelInvalid`.
- Export after labels: each line parses as JSON with the six keys; Debatable has `human_verdict` null.

Regression: `pnpm db:generate`, `pnpm db:migrate`, `pnpm test`, `pnpm lint`, `pnpm exec tsc --noEmit`, `pnpm build`.

## Done when

A user can Check scope, mark the verdict Correct / Wrong (with expected label) / Debatable, persist one snapshot row per history check (upsert on change), download only their cases as JSONL in the locked six-field contract, and cannot read or write another user’s evaluation rows. Unlabeled checks do not appear in the table or the file.

## Explicit non-goals (this slice)

- In-app evaluation analytics
- History-list labeling
- Shared team export
- Prompt/model changes driven by the dataset
- Storing replies, change orders, citations, or confidence on `evaluation_cases`
- Keyword fallback, silent defaults, or retries
