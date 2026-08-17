# Auth and Data Isolation Status

## Current Phase

Implemented with one environment blocker. `OPENAI_API_KEY` is set in `.env.local`, automated gates pass, scope upload helpers and OpenAI notice/footer copy are verified, but live `POST /api/analyze` returns `502 errors.analysisFailed` because OpenAI rejects requests from this region (`403 Country, region, or territory not supported` in server logs). Happy-path verdict/replies/change-order smoke is blocked until analyze succeeds from a supported region.

## Done

- LLM scope analysis wired: `POST /api/analyze` with OpenAI `gpt-4o-mini`, structured `AnalysisResult` validation, and no keyword fallback. Live happy-path `200 { result }` is **not** verified — OpenAI returns `403 Country, region, or territory not supported` from this region (`502 errors.analysisFailed` in smoke).
- Scope file upload on New Project for `.txt`, `.md`, and `.pdf` (5 MiB max, client text extraction; text-only storage in Postgres). Vitest covers `.txt`/`.md` accept and reject paths; `.pdf` browser upload not E2E-verified; Node/pdfjs manual extract failed (`DOMMatrix is not defined`).
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
- Live smoke with `OPENAI_API_KEY` present: register → project (Acme scope) → analyze attempted; history POST blocked when analyze fails; authenticated workspace HTML includes OpenAI copy and no “not analyzed by a real AI” disclaimer; `request-panel.tsx` renders `t('check.openaiNotice')`.

## In Progress

- Environment blocker: live OpenAI analyze from this region returns `502 errors.analysisFailed` (`403` in server logs). Happy-path verdict/replies/change-order smoke and history POST after analyze remain blocked.

## Next

- Retry live OpenAI analyze from a supported region so `POST /api/analyze` returns `200 { result }` with verdict, replies, and change order; then POST history and mark this slice complete.
- Optional: manual browser upload of `.txt` and `.pdf` on New Project UI once analyze path is unblocked.

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
- Live OpenAI analyze smoke skipped (prior session): `.env.local` had `DATABASE_URL` and `AUTH_SECRET` but no `OPENAI_API_KEY`.
- `pnpm db:up` passed; Postgres container healthy; `pnpm db:migrate` passed.
- Analyze API HTTP smoke (PowerShell `Invoke-WebRequest`, dev server on `localhost:3000`, no `OPENAI_API_KEY`):
  - `POST /api/analyze` without session cookie → `401` `{"error":"errors.authRequired"}`.
  - Register user, create project with non-empty scope, `POST /api/analyze` with `{ projectId, request }` → `503` `{"error":"errors.analysisUnavailable"}` (not a keyword verdict body).
  - Second user `POST /api/analyze` with first user's `projectId` → `404` `{"error":"errors.projectNotFound"}`.
- `pnpm test` passed after analyze smoke (2 files, 10 tests).
- `OPENAI_API_KEY` present in `.env.local` (value not logged).
- Live OpenAI analyze smoke (2026-08-17, key present): register `201`, create project `201`, `POST /api/analyze` → `502` `{"error":"errors.analysisFailed"}`; server log `openai_request_failed` with `403 Country, region, or territory not supported` (not a keyword-heuristic body).
- Authenticated `/` `200`: HTML contains OpenAI-related copy; old “not analyzed by a real AI” disclaimer absent.
- `pnpm test` passed after live smoke attempt (2 files, 10 tests).
- Tiny PDF `readScopeFile` manual check in Vitest/jsdom: failed `errors.scopeFileEmpty` after `scope_pdf_extract_failed` / `DOMMatrix is not defined`.
