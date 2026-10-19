# Standalone React Frontend Migration — Implementation Plan

Request: migrate ScopeCreepGuard from Next.js following approved design section 14.
Spec: `docs/design/project-draft-ai-workflow.md`, section 14.
Base: fetched `origin/main` **69727bd636ad5bce0bfa90fe0f5e84fb7d4e2c50**.
Branch: `codex/react-frontend-migration`, created directly at that SHA.
Checkout: existing checkout, clean before switch; no worktree, stash, reset,
rebase or cherry-pick. Current design branch tree matched main. No carried
document changes: section 14 is merged in PR35. Ignored AGENT.md/WORKLOG.md remain
local. No commits, pushes, PR/Linear updates or deployment are authorized.

## Goal, architecture and constraints

Replace Next.js application/runtime dependencies with React, TypeScript, Vite,
React Router data routing, use-intl and static Nginx delivery. Preserve existing
appearance, components, RU/EN catalogs and verified business behavior. Node is
build/development only. FastAPI owns auth/authorization; PostgreSQL owns confirmed
projects, Draft, immutable History and existing LLM workflows. No database or LLM
redesign, paid provider calls, application database migrations or unrelated
service/data changes. Execute inline with Superpowers executing-plans/TDD.

## Verified baseline and integration considerations

- PR33 autosave/concurrent-edit recovery and PR34 bounded reply similarity are
  merged; section 14 is merged in PR35. Translation commercial preservation,
  full assessment/independent client language and metrics fixes are on main.
- GitHub open-PR search returned none during planning; recheck before completion.
  Older local feature branches are not pending-fix authority. Carry no feature
  commits. If main moves during execution, report the recorded base, not a newer
  unverified base.
- Existing UI has `/`, `/login`, `/register`; workspace views use internal state.
  Existing `?draft=` and legacy imported-revision links must retain compatibility.
- Persistent provider has tested autosave/recovery behavior; legacy provider is
  a parallel application selected by SCOPE_GUARD_WORKFLOW_V2. Remove duplication
  after transferring relevant legacy test coverage to the persistent workflow.
- Durable command recovery currently covers analyses/regenerate/translate/estimate,
  not agreement preparation. Preserve/document that baseline limitation.
- Base Compose disables persistent workflow. Existing explicit workflow/LLM
  overlays reference older schema targets; compatible current head is
  `0007_nonblocking_llm`. Operator backup/backfill/check/cutover remains required.

## Responsibility replacement and public interfaces

| Existing Next responsibility | Replacement |
| --- | --- |
| App Router/layout/start/build | Vite entrypoint, React providers and RouterProvider |
| Internal view state | `/`, `/projects`, `/projects/new`, `/projects/:projectId/edit`, `/history`, `/drafts` |
| Login/register pages and JWT page guard | `/api/auth/me` session provider and client route guard |
| API route forwarders/proxy | Nginx `/api/*`; matching Vite development proxy |
| Origin checks | Existing FastAPI exact-Origin middleware |
| Upload/PDF size boundaries | Existing bounded FastAPI parsing, verified through proxy |
| next-intl server config/router.refresh | use-intl client provider, existing locale cookie/API |
| next/font | Bundled Geist/Geist Mono fonts and existing CSS variables |
| @vercel/analytics/next | Production-only React integration |
| Next entrypoint/healthcheck | Unprivileged Nginx runtime, `/health/live` |
| Next typegen/lint/harness launchers | Explicit TypeScript, React ESLint and SPA/proxy tests |

No backend public API/schema change is planned. Generated types move to
`src/shared/api/generated.ts`; source snapshot stays `ci/contracts/openapi.json`.
Keep jose/bcryptjs as development dependencies for frozen Python compatibility
fixtures until those tests no longer require them.

## Module and state boundaries

`src/app` owns startup/providers/routing and cross-feature composition. `pages`
compose auth, projects, analysis, drafts, history and change-orders public feature
interfaces. `shared` owns transport/error normalization/generated contracts,
business-free UI, validated public config, i18n and browser storage adapters.
Dependencies flow downward; no feature-private cross imports or cycles.

Session owns identity/bootstrap/expiry/activity. Project/history resource hooks
own confirmed resource lists. Draft editor owns its confirmed revision and local
edits; forms own unsaved input. Analysis/CO operations own operation progress,
not another editable Draft copy. Composition connects operations through the
editor's flush/revision/edit-token/guarded-response interface. Browser storage
retains preferences and unconfirmed recovery only, never server ownership.

Preserve DraftAutosave/user-patch/WorkflowOperations algorithms: 750ms debounce,
5s maximum interval, immediate structured edits, one in-flight save, coalesced
partial patches, frozen uncertain command IDs/payloads, bounded retries, server
ordering, different-field preservation, new typing over old acknowledgements,
owner/Draft/tab isolated recovery, revision-bound legacy recovery, explicit
conflict review, accurate save feedback, AI/history revision guards. Keep immutable
analysis/history distinct from mutable replies and commercial conditions.

## Routes, auth, localization and transport

- `/` remains scope check and existing `?draft=` target. `/check` replaces to `/`
  preserving query/hash. Auth routes remain `/login` and `/register`.
- Add `/projects`, `/projects/new`, `/projects/:projectId/edit`, `/history`,
  `/drafts`. Keep selected Draft in query; preserve unrelated query/hash.
- Imported legacy UUIDs stay read-only until explicitly closed. Missing/foreign
  links show errors, never silently load unrelated work.
- Keep workspace providers mounted across pages. Router navigation/back/forward
  share a save barrier. Flush before replacing Draft/project/logout; failed saves
  block navigation. Unsaved project forms need discard confirmation; retain
  beforeunload protection. Validate same-origin returnTo through authentication.
- Bootstrap identity once through `/api/auth/me` with browser identity lock.
  Distinguish outage from expiry. Dispose authenticated memory on owner change,
  retaining owner-isolated recovery/commands. No browser JWT secrets/tokens.
- use-intl preserves dictionaries/interpolation/formatting. Existing locale cookie,
  Russian default; POST `/api/locale` then update provider without remount/reload.
  Update document language/meta. UI locale never overwrites client-language
  selection or editor state. Existing results retain recorded language; new
  analysis receives current interface locale.
- Shared HTTP provides safe same-origin paths, credentials, cancellation, typed
  errors with status/fields/terminal metadata, raw response headers, JSON/form/blob
  support. No generic mutation retries. Feature operations retain polling/retry
  ownership. Preserve upload boundaries, download bytes and filenames.

## Container, runtime configuration and CI

Build static assets with Node, serve via unprivileged Nginx (`runner` target,
service `app`, container port3000). `/api` and `/api/*` never use SPA fallback;
missing assets404, page routes fall back to index. Hash assets immutable;
index revalidates; API is uncached. Static `/health/live` replaces Node probe.
Upstream configured at startup stays server-only. Browser config is public
same-origin only; remove frontend AUTH_SECRET/provider/env-proxy requirements.
Retain backend secrets, Origin settings and service names.

Forward exact paths/query/method/body, cookies/multiple Set-Cookie, Content-
Disposition, cache headers, request/idempotency/Retry-After headers. Never retry
mutations/follow redirects. Preserve cancellation and sufficient operation timeouts.
Transport failure is sanitized JSON503. Reuse backend body limits without generic
proxy HTML replacing typed errors. Verify incoming routing headers cannot select
another upstream. API errors pass through unchanged.

Update existing CI scripts and compatibility/image harnesses rather than deleting
meaningful coverage. Replace Next launchers/redirect assertions at the new owner.
Preserve `rebase` job and contract locations. Explicit coordinated rollout targets
existing0007 head; do not migrate real data. Disabled persistent workflow is a
reported deployment prerequisite, not a second frontend mode.

## Ordered tasks and completion checks

- [x] Task1: fetch/record baseline, safe branch creation, save this plan.
- [x] Task2: Vite shell, routes, localization/fonts/styles; test reload/navigation
  and locale persistence without editor remount.
- [x] Task3: session/HTTP/development proxy; verify auth destination/cookies,
  expiry/outage, uploads/downloads and error metadata.
- [x] Task4: split persistent state, migrate feature UI/tests, remove legacy
  provider and Next application paths after coverage passes.
- [x] Task5: Nginx image, Compose/runtime config, CI/harness updates. Verify image
  and real proxy security/limits/caching/cancellation.
- [x] Task6: full checks, disposable Compose and controlled-provider browser
  regression; final independent review, fix findings and update this record.

Each task adds/adapts focused behavior coverage before replacement, runs it and
records evidence. No per-task commits. Rulings/deviations go here and local journals.

## Verification matrix and acceptance

Run focused tests, then frontend lint/typecheck/full suite/build, API type/OpenAPI
freshness, applicable backend tests/static checks, image build and Compose smoke.
Use isolated labelled disposable databases, synthetic identities, controlled
provider responses and private test export storage. Sanitize inherited settings.
Cleanup only task-owned resources. Do not touch user DBs or paid providers.

Real browser against built static container:
1. New user/empty projects gives clear next action.
2. Project create/edit; email/end date survive clean authenticated browser context.
3. Verdict, full assessment and reasoning.
4. Interface/client language separation.
5. Manual client language persists through reload.
6. Regenerate changes only selected tone.
7. Manual commercial terms and explicit currency conversion persist.
8. Independent Change Order preparation.
9. Actual clipboard and PDF download through proxy.
10. Immutable History versus editable Draft.
11. Two tabs: same-field ordering and distinct-field preservation.
12. Network/503, bounded retries, failed indicator, retained edits/recovery.
13. Reload/direct/legacy links, back/forward, guarded failed navigation.
14. Login/logout/expiry/returnTo/cross-user isolation.
15. Browser identity/activity/operation metrics without duplicate effect mutations.

Also test unknown API/asset paths, multiple cookies, multipart oversize limits,
headers, PDF filename/bytes, caching and cancellation through Nginx. Compare
failures to baseline fixtures; log existing defects without scope expansion.
Controlled-provider tests establish workflow behavior, not live model quality.

## Evidence and handoff

Planning baseline:8files/79focused tests passed; initial sandbox runner failed
before execution, authorized rerun passed. Docker engine29.8.2 available. Fetch
completed2026-10-19; main unchanged at69727bd. Branch created directly there after
sandbox Git index-lock denial was resolved with normal authorization.

Completion requires applicable green checks, tested image/Compose, browser matrix,
no Next runtime/application dependency and one persistent frontend. Final report
records ancestry, completed steps, structure, replaced responsibilities, changed
config, actual results/limitations, pending-PR recheck and exact run commands.
Operator owns deployment and real-data cutover; this task leaves changes uncommitted.

### Task2–4 progress and rulings
Vite/router/use-intl/font dependencies locked; React19.2.7 patch required by router8.5 peer contract. Runtime session/project/editor/analysis/agreement/history responsibilities extracted; no runtime legacy provider remains.60 migrated/new focused tests passed. Router owns history bookkeeping: retain legacy application state under usr and assert its preservation, not exact raw history shape. Archive response updates confirmed project history immediately. Retired legacy tests for explicit CreateDraft/proof/local-only project fields are replaced by persistent navigation/store coverage plus new project-resources/client-language-workflow tests; immutable fixture/crypto compatibility tests remain. No baseline legacy-mode business policy is substituted for v2 publication policy.


### Implementation and review record — 2026-10-20

All six implementation stages are delivered, with the verification limits below.
HEAD is still the fetched baseline: no commits were created. GitHub open-PR search
`repo:gushinets/ScopeCreepGuard is:pr is:open` returned no open PRs at handoff.
There are no pending feature branches included or pending-PR integration changes.

The final source layout is `frontend/src/app`, `pages`, all six specified domain
features and `shared/{api,ui,config,i18n,storage}`, plus test-only fixtures in
`src/test`. Feature public exports/contracts and the dependency-check script
prevent private cross-feature imports, upward imports and runtime cycles.
Application composition is separate from session, project resources, the active
Draft/autosave controller, analysis progress, agreement commands and History.
There is no second application, broad runtime StoreValue, legacy StoreProvider,
PersistentStoreProvider or frontend workflow flag. The compatibility provider/lens
in `src/test/workspace.tsx` composes the actual feature contexts for existing tests.
Reusable document/crypto/browser-buffer compatibility algorithms and their tests
remain; they do not own confirmed resources. Old feature-placeholder READMEs were
removed. The generated API file is now `src/shared/api/generated.ts`; contracts
remain in `ci/contracts` unchanged. No backend runtime/schema/business code changed.

Next responsibility replacements:

| Removed responsibility | Delivered replacement |
| --- | --- |
| Next startup/build/server renderer and font loader | Vite, explicit TypeScript check, static index and bundled Geist/Mono Latin/Cyrillic assets |
| Server page guards and signed-session helper | Auth/me session provider and router UI guards; FastAPI remains authoritative |
| Internal view switching / framework navigation | React Router data router, persistent authenticated layout, save/form barriers, query/hash-compatible routes and same-origin returnTo |
| next-intl server configuration | use-intl provider, existing RU/EN catalogs, locale cookie/API and document metadata |
| Route-handler forwarding / Origin helper / proxy.ts | Vite development forwarding and unprivileged Nginx static proxy; existing FastAPI Origin/auth/limit checks |
| Next standalone Node runtime and healthcheck | Nginx runner on port3000, static /health/live, API errors outside SPA fallback |
| Next presets/type generation/harness launch | ESLint TS/React rules, boundary checker, tsc/Vite and updated HTTP/container harnesses; rebase job retained |

Independent review found three migration regressions: workspace unmount on a
background session-service outage; stale analysis progress after project changes;
and a late project-list refresh overwriting newer resource mutations. Focused
regressions were observed failing, then fixed: keep the authenticated workspace
mounted with an outage notice, clear progress on controller replacement, and
sequence resource refreshes against mutations. The three focused files passed
23 tests. A subsequent explicit project-form discard test also passed alongside
the outage test (2 tests).

Ruling: keep Nginx upstream resolution at startup instead of assuming Docker's
embedded DNS exists on every network — the hard-coded resolver broke standalone
Docker bridge requests. Compose and standalone Docker checks now pass. Operators
must restart app after a backend address replacement; README states this cost.
Ruling: the native controlled-provider fixture excludes server-owned labels and
supplies translation commercial metadata — obsolete fixture fields caused a
semantic rejection, not a frontend or live-provider defect. The corrected fixture
uses the real SQL workflow, LLM worker and PDF export worker with a local adapter.
Ruling: preserve baseline currency behavior. The baseline changeCurrency handler
only changes the currency field and performs no arithmetic conversion/rate lookup.
An explicit conversion calculator is absent from this baseline and is not added.
Ruling: agreement preparation's durable-command recovery omission is retained as
recorded above; adding that workflow behavior is outside this runtime migration.

### Executed verification

Evidence is retained locally under ignored `output/react-migration` and
`output/playwright`; private fixture state/database credentials are not published.

| Boundary | Executed result / evidence |
| --- | --- |
| Full frontend regression | 49 files / 344 tests passed in the final complete run; `unit-completion.log` |
| Added form discard/outage coverage | 2 focused tests passed; then both were included in the final complete suite |
| Lint / architecture / TypeScript | ESLint passed, 90 production modules passed dependency/cycle checks, tsc passed; lint-final-reviewed/typecheck-final logs |
| Contracts | API generated-type freshness and Python OpenAPI snapshot freshness passed; snapshot unchanged |
| API auth / exact Origin / HTTP contracts | 59 tests passed; `api-regression-final.log` |
| Retained gateway harnesses | Auth/project 15+14 checks passed; generation and draft compatibility journeys passed with zero provider calls |
| Production images | React Nginx runner and existing API image built; image-completion and backend-image logs |
| Actual static proxy | 20 checks passed: page fallback, missing assets, methods/query/body/cookies, separate Set-Cookie, header filtering, binary PDF/filename, no replay, Retry-After, errors/cache and upstream cancellation; `proxy-completion.log` |
| Actual API/frontend images | 11 checks passed: cookie auth, multilingual PDF bytes/filename, unchanged saved snapshot, Markdown/PDF multipart extraction, oversized upload413, foreign-Origin403 and unauthorized download401; `runtime-completion.log` |
| Actual Compose definitions | 11 checks passed using a unique project/volume, persistent schema, no provider, project creation and confirmed Draft PUT/reload; `compose-completion.log`; owned stack/network/volume removed |
| Real development browser | Vite login/registration, locale switch to English, project form/create and active saved Draft passed; react-dev-register/create/check logs/snapshots |
| Static-container real browser | Acceptance matrix below; actual controlled API, disposable PostgreSQL and actual workers |

The initial Windows fork runner and several redundant reruns were interrupted
by tool-runtime restarts/host commit-memory exhaustion. After closing task-owned
test processes, the final full run used one Vitest thread and passed all344 tests.
The added test's Testing Library options were corrected during final TypeScript
validation. The final Nginx configuration explicitly enables SNI and certificate
validation for HTTPS upstreams using its verified system CA bundle; it was rebuilt
and its proxy/image/Compose checks were repeated. No React application code changed
after its successful full suite/browser verification. One automatic approval attempt also failed on an account
usage limit before execution; the authorized continuation completed the necessary
checks through the normal approval path. No approval bypass was used.

### Real-browser acceptance evidence

| Requested scenario | Observed result |
| --- | --- |
| Empty account | Clear New project action; registration/authenticated empty state |
| Projects | Create and edit; contact email and end date restored in a fresh authenticated context without editor storage |
| Verdict/assessment | Out-of-scope, confidence, full reasoning/citations/estimate/next action visible |
| Languages | English analysis with automatically detected Spanish reply; manual English override persisted through reload; RU/EN interface changes retained editor/client selection |
| Regenerate/commercial terms | Only selected Firm text changed; other tones and current manual hours/amount/currency unchanged |
| Independent agreement | Initial check had no Change Order; explicit preparation added it afterwards |
| Copy/PDF | Actual clipboard equals displayed reply; archived/finalized agreement exported/downloaded; valid one-page26461-byte PDF contains Fixture Provider |
| History/Draft | Archive/open leaves working Draft separate; later Draft edits did not alter archived content |
| Concurrent tabs | Different-field edits both preserved; later server-ordered same-field edit restored on reload |
| Save failures | Controlled503 caused three attempts with one operation ID; failed navigation retained text; local recovery survived reload and restored confirmed state; real offline mode retained edits and retried |
| Delayed acknowledgement | New typing during an in-flight delayed save remained visible and was confirmed afterwards |
| Navigation | Direct edit/history links, reload, back/forward, draft query plus unrelated query/hash, complete returnTo and failed-save barrier passed; form discard cancellation/acceptance covered by actual-router component tests |
| Session/isolation | Logout/login/expiry, same-browser second user, owner resource404 and hidden foreign recovery; original owner recovered retained edits after reauthentication |
| Metrics | Expected requested/completed events for two checks, one regeneration, one translation and one finalized export; zero duplicate operation/event pairs; real interaction endpoint204 plus trusted-event unit coverage |

Captured workspace screenshot was visually inspected; styling and typography are
preserved. `react-change-order.pdf` was parsed to verify content, in addition to
binary download tests. The final native beforeunload recovery prompt was observed;
subsequent Saved state and confirmed text were checked separately.

### Handoff / limits / operator-owned work

- Start development from frontend: `corepack pnpm install --frozen-lockfile`, then
  `corepack pnpm dev`; API_ORIGIN defaults to http://127.0.0.1:8000. Configure the
  persistent API/LLM/export workers as documented in README, with the public
  origin in the backend allowlist. Secrets belong only to backend/workers.
- Build: `docker build --target runner -t scope-guard-frontend frontend`.
  Coordinated deployment: `docker compose -f compose.yaml -f compose.workflow.yaml
  -f compose.llm.yaml up --build -d` after explicit backup/backfill/verification and
  required database/private-export/model/rate-bound configuration. This command
  was not run against application data. The disposable harness tested the same
  base service definitions with provider disabled and owned test configuration.
- Production cutover, public TLS/edge deployment and real external export storage
  remain operator-owned and were not exercised. Mocked-provider success proves
  workflow behavior, not live model quality. No paid provider was contacted.
- Legacy imported-revision link resolution has retained persistent component
  coverage; a separately seeded legacy-import browser journey was not repeated.
- The existing optional Vercel Analytics integration requests a missing Vercel
  endpoint on this non-Vercel host. Product activity/metrics are independent and
  verified. No analytics hosting change was added.
- The Vite build warns about the existing large main bundle (about602kB before
  gzip). Route chunk optimization is a future performance task, not a behavior
  migration prerequisite.
- Base Compose deliberately does not silently activate the persistent workflow.
  The overlays now target compatible0007; API/worker/frontend rollout must match.
- Changes remain unstaged/uncommitted for review. Local journals stay ignored.
  Test images/artifacts are retained; task-created services and disposable data
  are cleaned up. No deployment, push, PR, merge, Linear or application DB action.

### Publication follow-up — 2026-10-20

The user explicitly authorized committing, pushing and creating a PR after
reviewing the local preview. This supersedes the initial uncommitted handoff.
Fetched origin/main again: unchanged at 69727bd636ad5bce0bfa90fe0f5e84fb7d4e2c50.
Fresh pre-publication verification passed: 49 files / 344 frontend tests,
ESLint, dependency boundaries (90 modules), TypeScript, Vite production build
and generated API type freshness. Log: output/react-migration/pr-unit.log.
The existing 602.42 kB bundle warning remains. Four trailing blank lines were
removed for a clean staged whitespace check. No application behavior changed.
The global pnpm wrapper attempted a dependency reinstall; checks were instead
run directly with the already installed tools. Preview services and their
exact disposable database were stopped and removed at the user's request.
Local AGENT.md / WORKLOG.md, private fixture state and output remain ignored.
Publication targets codex/react-frontend-migration -> main; no merge authorized.

### PR #36 review follow-up — superseded project selection errors

Confirmed review discussion r4319875484: a delayed failure for project B could
report against a newer project C because only selection success was guarded.
The UI selection handler now captures its navigation token and reports failures
only while that token is current. Added three regression cases: stale 503 before
and after C installs, and a still-current 503 that must remain visible. Both
stale cases failed before the fix; all 19 navigation tests pass after it.
Focused ESLint, all 90 module boundaries and TypeScript pass. No container or
backend change; the full migration suite was not repeated for this narrow fix.
