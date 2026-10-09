# Auth and Data Isolation Test Plan

> Layout note (ANY-638): application paths and pnpm commands in this document
> are relative to `frontend/`. Local application configuration is `frontend/.env*`;
> root Compose commands explicitly use `docker compose -f compose.yaml`. Historical
> milestones below retain their original context; see root README for current setup.

## Critical Paths

- Register a new user with a valid email and password.
- Reject invalid email, duplicate email, and short password.
- Login with the registered credentials.
- Reject an incorrect password without creating a session.
- Logout clears the session and returns to login.
- Create a project and run a scope check.
- Verify the check is saved to that user's project history.

## Isolation Checks

- User A creates a project.
- User B sees an empty project list after registering or logging in.
- User B cannot load or write history to User A's project id.
- Unauthenticated requests to protected project endpoints return unauthorized.

## Commands

- `docker compose up -d`
- `pnpm db:migrate`
- `pnpm lint`
- `pnpm build`

## Release Gate

The feature is ready when the auth flow works end to end and no project or history record can be accessed without a matching authenticated `user_id`.

# English / Russian UI Internationalization Test Plan

## Critical Paths

- First visit with no `locale` cookie renders Russian UI and `html lang="ru"`.
- The EN/RU switcher changes the `locale` cookie and refreshes the current route.
- Login and register pages translate labels, descriptions, placeholders, validation errors, submit states, and links.
- Authenticated workspace translates nav, loading/error states, project screens, history screens, request form, result chrome, reply controls, change-order labels, verdict chips, industry labels, and dates.
- User-entered project names, project scopes, client requests, stored history summaries, and generated analysis/reply/change-order body text remain unchanged.

## Error Checks

- Invalid email, short password, duplicate account, invalid login, unauthenticated API access, invalid project data, invalid history data, and malformed JSON return stable error keys.
- Visible client errors are translated through the active message catalog.
- Missing or invalid config remains a logged server invariant and is not shown as localized UI copy.

## Commands

- `pnpm lint`
- `pnpm exec tsc --noEmit`
- `pnpm build`

## Release Gate

The feature is ready when Russian is the default first-load language, EN/RU switching updates all UI chrome and user-facing errors, and saved/generated content remains unchanged.

# LLM Analyze + Scope File Upload Test Plan

## Critical Paths

- Upload `.txt` / `.md` / `.pdf` into New Project; reject files larger than 5 MiB and extensions such as `.docx`.
- Check scope with a valid `OPENAI_API_KEY` → verdict, client replies, change order, and history entry.
- Check scope uses `gpt-5.4-nano` with reasoning; result still includes verdict, three replies, Change Order, and history.
- Missing `OPENAI_API_KEY` → `errors.analysisUnavailable` / error UI (no keyword verdict).
- User B cannot analyze User A's project id (`404`).
- OpenAI notice is visible on the request panel; footer no longer claims requests are not analyzed by a real AI.
- Prompt regression: `pnpm exec vitest run lib/llm/prompt.test.ts` (new labels present; old few-shots absent).
- Incomplete model responses surface `errors.analysisFailed` (no fabricated verdict).
- Unusable model output (invalid JSON or shape failure) surfaces `errors.analysisInvalid` (no fabricated verdict).

## Commands

- `pnpm test`
- `pnpm lint`
- `pnpm exec tsc --noEmit`
- `pnpm build`
- `docker compose up -d` and `pnpm db:migrate` (live smoke with `.env.local` including `OPENAI_API_KEY`, `DATABASE_URL`, and `AUTH_SECRET`)

## Release Gate

The feature is ready when scope checks use OpenAI only (no keyword fallback), uploads enforce size and format rules, ownership isolation holds on `/api/analyze`, and missing-key failures show the correct localized error instead of a fabricated verdict.

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
