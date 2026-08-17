# Auth and Data Isolation Status

## Current Phase

Complete. LLM scope analysis and scope file upload verified with automated checks; live OpenAI smoke skipped because `OPENAI_API_KEY` is not set in `.env.local`.

## Done

- LLM scope analysis via `POST /api/analyze` with OpenAI `gpt-4o-mini`, structured `AnalysisResult` validation, and no keyword fallback.
- Scope file upload on New Project for `.txt`, `.md`, and `.pdf` (5 MiB max, client text extraction; text-only storage in Postgres).
- OpenAI informational notice on the request panel; footer no longer claims requests are not analyzed by a real AI.
- Stable API error keys `errors.analysisUnavailable` and `errors.analysisFailed` with EN/RU client translation.
- Plan confirmed: email/password auth, local Postgres, per-user data isolation.
- Execution docs created.
- Postgres Docker Compose, Drizzle schema, migration, and env examples added.
- Email/password register/login/logout/me API added.
- Session cookie auth and protected route middleware added.
- Projects and history APIs are scoped by authenticated user id.
- Client store now loads projects from API and writes new projects/history to Postgres.
- Live Docker smoke completed after daemon became available.
- English/Russian UI switching added with `next-intl`, Russian default locale, locale cookie switching, localized chrome, and stable API error keys.

## In Progress

- None.

## Next

- None for this feature.

## Decisions

- Auth identifier is a unique normalized email.
- Sessions use signed httpOnly cookies.
- The database is the source of truth for projects and history.
- Newly registered users start with no projects.
- Internationalization keeps existing URLs unchanged and stores language in a `locale` cookie.
- Russian is the default locale for first visits with no cookie.
- User-entered content and generated analysis/history copy stay as stored.

## Validation Log

- `pnpm db:generate` passed and created `drizzle/0000_keen_malcolm_colcord.sql`.
- `docker compose up -d` passed; container `scope-creep-guard-postgres` is healthy.
- `pnpm db:migrate` passed.
- `pnpm lint` passed.
- `pnpm build` passed.
- `pnpm exec tsc --noEmit` passed.
- Live API smoke passed: register/login/logout/me, validation errors, duplicate email, empty project list for new users, project/history write for owner, 404 isolation for non-owner, unauthenticated `/` redirects to `/login`.
- `pnpm lint` passed after i18n changes.
- `pnpm exec tsc --noEmit` passed after i18n changes.
- `pnpm build` passed after i18n changes. Next.js reported the existing middleware-to-proxy deprecation warning.
- i18n HTTP smoke passed: no-cookie `/login` returned `html lang="ru"` and Russian text; `/api/locale` switched to English and Russian; invalid login returned `errors.invalidCredentials`; authenticated `/` returned matching `html lang` and localized workspace loading copy for both locales.
- `pnpm test` passed (Vitest: `lib/llm/schema.test.ts`, `lib/scope/read-file.test.ts`).
- `pnpm lint` passed after LLM analyze and scope upload changes.
- `pnpm exec tsc --noEmit` passed after LLM analyze and scope upload changes.
- `pnpm build` passed after LLM analyze and scope upload changes.
- Live OpenAI analyze smoke skipped: `.env.local` has `DATABASE_URL` and `AUTH_SECRET` but no `OPENAI_API_KEY`.
- `pnpm db:up` passed; Postgres container healthy; `pnpm db:migrate` passed.
- Analyze API HTTP smoke (PowerShell `Invoke-WebRequest`, dev server on `localhost:3000`, no `OPENAI_API_KEY`):
  - `POST /api/analyze` without session cookie → `401` `{"error":"errors.authRequired"}`.
  - Register user, create project with non-empty scope, `POST /api/analyze` with `{ projectId, request }` → `503` `{"error":"errors.analysisUnavailable"}` (not a keyword verdict body).
  - Second user `POST /api/analyze` with first user's `projectId` → `404` `{"error":"errors.projectNotFound"}`.
- `pnpm test` passed after analyze smoke (2 files, 10 tests).
