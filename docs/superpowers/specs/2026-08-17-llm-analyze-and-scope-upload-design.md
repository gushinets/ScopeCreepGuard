# Design: LLM Analyze + Scope File Upload

Date: 2026-08-17  
Source: `idea-006-scope-creep-guard-2026-05-25.md`, `scope-creep-guard-prd.md`  
Slice: A — web prototype improvements (not Chrome Extension / full product)

## Goal

Replace client-side keyword analysis with OpenAI, and let users load project scope from `.txt`, `.md`, or `.pdf` into the existing New Project flow. Preserve auth, per-user isolation, EN/RU UI chrome, and the current check → verdict → reply → Change Order → history scenario.

## Decisions (locked)

| Topic | Choice |
|---|---|
| Product slice | Web only: LLM + file upload |
| LLM provider | OpenAI via `OPENAI_API_KEY` |
| Model | `gpt-4o-mini` |
| File formats | `.txt`, `.md`, `.pdf` (no `.docx` in this slice) |
| PDF parsing | Client-side (pdf.js); store extracted text only |
| Privacy UX | Short informational notice before Check scope (no consent checkbox) |
| Keyword fallback | None — fail fast on missing key, API errors, or invalid model JSON |
| Max upload size | 5 MiB per file (client reject before read) |
| Out of scope | Chrome Extension, onboarding questionnaire, DOCX, billing, at-rest encryption, personal “voice” learning |

## Architecture

Keep Next.js App Router + Postgres + session cookies.

### Analyze flow

1. User selects a project (scope already in DB) and enters a client request.
2. Client `POST /api/analyze` with `{ projectId, request }`.
3. API verifies session, loads the project **owned by** the current user, calls OpenAI with scope + industry + request.
4. Model returns structured JSON matching `AnalysisResult`.
5. Client renders the existing result UI; history is written via the existing history endpoint.

### Scope upload flow

1. On New Project, user can paste text or upload a file.
2. `.txt` / `.md` → `FileReader` → textarea.
3. `.pdf` → pdf.js on the client → textarea.
4. Save project unchanged: Postgres stores extracted text only (no binary file storage).

### Config

- `OPENAI_API_KEY` required for analysis (document in `.env.example`).
- Missing key or OpenAI failure → stable user-facing error key; no silent keyword path.

## Components and data flow

| Module | Responsibility |
|---|---|
| `app/api/analyze/route.ts` | Auth, ownership, OpenAI call, validate JSON, return `AnalysisResult` |
| `lib/llm/openai.ts` | Chat Completions (or equivalent) with structured output; fail if key missing |
| `lib/llm/prompt.ts` | System/task prompt: scope, industry, request; in / borderline / out rules; EN replies + Change Order |
| `lib/llm/schema.ts` | Validate model output against `AnalysisResult` |
| `lib/scope/read-file.ts` | Client helper: read `.txt`/`.md`/`.pdf` → string; reject empty extract / file > 5 MiB |
| `components/scope-guard/new-project-view.tsx` | Upload control fills scope textarea |
| `components/scope-guard/request-panel.tsx` | OpenAI notice near Check scope |
| `components/scope-guard/store.tsx` | `runCheck` calls `/api/analyze` instead of local `analyzeRequest` |
| `lib/analyze.ts` | Delete after store migrates (no keyword path left in the app) |
| `middleware.ts` | Keep `/api/analyze` behind the same auth gate as other protected APIs |

```
[New Project]
  file → client extract → scope textarea → POST /api/projects → Postgres

[Check Scope]
  request + projectId → POST /api/analyze
    → session user
    → project WHERE id AND user_id
    → OpenAI(scope, industry, request)
    → AnalysisResult
  → result panel
  → POST .../history (existing)
```

**Boundaries**

- Client: UI, file text extraction, notice, display.
- Analyze API: auth, ownership, LLM, response shape.
- Projects API: unchanged contract (`scope` is text).

## Error handling

| Situation | Behavior |
|---|---|
| No session | `401` + stable error key |
| Foreign / missing `projectId` | `404` |
| Empty request or empty scope | `400` before OpenAI |
| Missing `OPENAI_API_KEY` | Server logs invariant; client gets `errors.analysisUnavailable` |
| OpenAI timeout / 5xx / invalid JSON | Structured log → `errors.analysisFailed`; UI error + Retry |
| PDF with no text / file > 5 MiB | Client error before save; do not invent empty or partial scope |
| Verdict outside enum | Treat as invalid model response → `errors.analysisFailed` |

OpenAI notice is informational and non-blocking.

## Testing

- Unit: LLM response schema validation (valid vs invalid JSON).
- Helper: `.txt` extract; PDF fixture with known text.
- API smoke: login → create project → analyze → history; other user’s project → 404.
- UI smoke: upload txt/pdf → text in scope; Check scope → verdict + reply + Change Order for out-of-scope; notice visible; clear error without key / on API failure.
- Regression: `pnpm lint`, `tsc --noEmit`, `build`; new EN/RU message keys.

## Done when

A user can upload `.txt`/`.md`/`.pdf` into a project, run a real OpenAI scope check, get verdict / English reply / Change Order, see a history entry, cannot access another user’s projects, and never receives a keyword-heuristic verdict when the LLM path fails.

## Explicit non-goals (this slice)

- Chrome Extension selection capture
- Onboarding questionnaire / voice pattern memory
- DOCX upload
- Storing original PDF binaries
- Billing / Amplitude / money-saved survey
- Claiming NDA-safe or legally binding Change Orders
