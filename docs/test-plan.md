# Auth and Data Isolation Test Plan

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

- Upload `.txt` / `.pdf` into New Project; reject files larger than 5 MiB and extensions such as `.docx`.
- Check scope with a valid `OPENAI_API_KEY` → verdict, client replies, change order, and history entry.
- Missing `OPENAI_API_KEY` → `errors.analysisUnavailable` / error UI (no keyword verdict).
- User B cannot analyze User A's project id (`404`).
- OpenAI notice is visible on the request panel; footer no longer claims requests are not analyzed by a real AI.

## Commands

- `pnpm test`
- `pnpm lint`
- `pnpm exec tsc --noEmit`
- `pnpm build`
- `docker compose up -d` and `pnpm db:migrate` (live smoke with `.env.local` including `OPENAI_API_KEY`, `DATABASE_URL`, and `AUTH_SECRET`)

## Release Gate

The feature is ready when scope checks use OpenAI only (no keyword fallback), uploads enforce size and format rules, ownership isolation holds on `/api/analyze`, and missing-key failures show the correct localized error instead of a fabricated verdict.
