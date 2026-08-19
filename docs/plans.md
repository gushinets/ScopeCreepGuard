# Auth and Data Isolation Plan

## Goal

Add email/password registration and login backed by local Postgres, then isolate projects and check history by the authenticated user.

## Milestones

### 1. Database and Configuration

- Add local Postgres through Docker Compose.
- Add Drizzle schema for users, projects, and history entries.
- Add migration tooling and required environment variables.

Definition of done: the database can be started locally and migrated from a clean checkout.

Validation:

- `docker compose up -d`
- `pnpm db:migrate`

### 2. Authentication

- Add register, login, logout, and current-user endpoints.
- Store sessions in a signed httpOnly cookie.
- Require valid sessions for the app and protected API routes.

Definition of done: a user can register with email/password, log out, log back in, and blocked routes redirect to login.

Validation:

- `pnpm dev`
- Manual register/login/logout flow in the browser.

### 3. User-Owned Project Data

- Replace shared client-side project state with project/history API calls.
- Scope all project queries and writes to the authenticated user's id.
- Return 404 for project ids not owned by the current user.

Definition of done: two users cannot see or write each other's projects or history.

Validation:

- Register user A, create a project, log out.
- Register user B and verify the project list is empty.
- Directly request user A's project id as user B and verify access is denied.

## Stop-and-Fix Rule

If an auth, database, or ownership check fails, stop feature wiring and fix the failing layer before continuing.

# English / Russian UI Internationalization Plan

## Goal

Add English/Russian UI switching with Russian as the default language, keeping existing URLs unchanged and translating user-facing API errors on the client.

## Milestones

### 1. i18n Setup and Catalogs

- Add `next-intl` configuration for App Router without locale-prefixed routes.
- Use `ru` as the default locale when the `locale` cookie is missing.
- Add complete `messages/ru.json` and `messages/en.json` catalogs.
- Configure the root layout to set `html lang`, load messages, and include Cyrillic font support.

Definition of done: a first visit renders through `next-intl` with `html lang="ru"` and complete Russian/English message catalogs.

Validation:

- `pnpm lint`
- `pnpm exec tsc --noEmit`

### 2. Localized API Errors

- Return stable error keys from auth, project, history, and middleware validation paths.
- Translate those keys in client-visible error states.
- Keep internal invariant and configuration errors in logs only.

Definition of done: user-facing API validation and auth errors render in the selected language.

Validation:

- Submit invalid auth and project forms in Russian and English.
- Confirm JSON API errors remain stable keys.

### 3. UI Chrome Extraction

- Replace hardcoded UI chrome across auth, navigation, project, history, request, result, reply, and change-order components.
- Add a compact EN/RU language switcher on auth pages and inside the authenticated app header.
- Localize dates, verdict labels, industry labels, and example request labels.
- Leave user-entered content and generated analysis/history text unchanged.

Definition of done: switching RU/EN updates all UI chrome without changing saved project data or generated analysis copy.

Validation:

- `pnpm lint`
- `pnpm exec tsc --noEmit`
- `pnpm build`
- Manual RU/EN smoke on login and authenticated workspace.

# LLM Analyze + Scope File Upload Plan

## Goal

Replace keyword scope analysis with OpenAI via authenticated `POST /api/analyze`, and let users load project scope from `.txt` / `.md` / `.pdf` on New Project.

## Milestones

### 1. LLM Pipeline and API

- Add OpenAI client (`gpt-4o-mini`, strict JSON schema) and `AnalysisResult` validation.
- Add `POST /api/analyze` with session auth, project ownership, and stable error keys.
- Remove keyword `lib/analyze.ts`; client `runCheck` calls `/api/analyze`.

Definition of done: scope checks require a valid `OPENAI_API_KEY`; missing key or OpenAI failure surfaces `errors.analysisUnavailable` / `errors.analysisFailed` (no fake verdict).

Validation:

- `pnpm test`
- `pnpm lint`
- `pnpm exec tsc --noEmit`

### 2. Scope Upload and UX

- Client file reader for `.txt` / `.md` / `.pdf` with 5 MiB limit and rejection of other extensions (e.g. `.docx`).
- OpenAI informational notice on the request panel; footer copy updated for OpenAI usage.

Definition of done: upload populates the scope textarea; only extracted text is stored; OpenAI notice is visible without a consent checkbox.

Validation:

- `pnpm test`
- `pnpm build`
- Manual upload smoke on New Project; analyze with and without `OPENAI_API_KEY`.

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
- Fail incomplete / empty / API errors with `errors.analysisFailed`; invalid JSON or shape failure with `errors.analysisInvalid`.

Definition of done: Check scope uses the new rules on `gpt-5.4-nano`; UI still shows confidence, three tones, Change Order, and history.

Validation:

- `pnpm test`
- `pnpm lint`
- `pnpm exec tsc --noEmit`
