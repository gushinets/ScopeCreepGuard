# ANY-805 frontend dependency security implementation plan

Approved by the user on 2026-11-02. Issue: https://linear.app/paveldik/issue/ANY-805.

## Goal and checkout

Remove High/Critical findings from frontend build/test paths without absorbing
ANY-802 (analytics/Next.js/Sharp) or ANY-804 (shadcn/MCP/Express). Base:
`03bda2de6afd2dabd90873fb6a9dfc08e7b89a49`; branch:
`codex/any-805-frontend-security`. Fetch confirmed the existing primary checkout
already matches origin/main. No worktree, merge, cherry-pick, reset or automatic
stash. Preserve three untracked architecture reports and private WORKLOG files.

## Ordered implementation

- [x] Establish clean frozen-install baseline with pnpm 10.34.1 and current Node 22.
- [x] Group 1: resolve direct/Tailwind PostCSS 8.5.6/19/23/26 to 8.5.32.
- [x] Group 2: resolve CSS source-map-js 1.2.1 to 1.2.2 and nanoid 3.3.11/16/18 to 3.3.20.
- [x] Group 3: retain jsdom 30.1.1, resolve undici 8.11.2 to 8.12.3.
- [x] Group 4: retain ESLint 9 and typescript-eslint; refresh brace-expansion
  1.1.18 to 1.1.21 and 5.0.6 to 5.0.12 independently, js-yaml 4.3.1 to 4.3.2.
- [x] Group 5: retain React Hooks 7.1.1; resolve browserslist 4.28.1 to 4.29.5,
  Hooks-specific Zod 3.25.76 to 4.6.7.
- [x] Group 6: re-audit paths and address only residual in-scope High/Critical.

Use compatible parent ranges before overrides, generated pnpm lockfile edits only,
and a verified coherent commit per group. Keep Tailwind 4.3.3, ESLint 9,
TypeScript 5.7.3 and Vite 8.2.4. No product/API changes or weakened checks.
If normal resolution retains Zod 3, use only
`eslint-plugin-react-hooks@7.1.1>zod: 4.6.7`: Hooks and zod-validation-error
accept Zod 4. Remove when the parent naturally resolves patched Zod.
Do not force shadcn's Zod consumers or brace-expansion's independent majors.
Align Node engines with existing jsdom's ^22.22.2 || ^24.15.0 || >=26.0.0.

## Verification and evidence

Heavy evidence belongs in ignored `output/any-805/`. Capture base/final revisions,
local changes, audits and dependency paths before/after, image IDs and labels.
For each CSS group run build, full tests and CSS comparison; for DOM run full
tests; for lint/Hooks run lint/boundaries, typecheck, API freshness and full tests.
Final clean frozen install, all those checks, production build, documented
frontend/gateway checks, official root Compose app build and representative
browser checks of authentication, projects, results and draft/agreement forms.
Use disposable full-stack infrastructure with private storage and controlled
responses; no paid LLM calls, existing database resets, volume deletion, Docker
pruning or interference with unrelated services. Infrastructure failures are
blocked checks, never passes. Zero High/Critical on owned paths is required.

## Delivery and ownership

Push and open a main-targeted PR with linear history; do not merge or update
Linear status. Include base/final SHAs, paths and versions/advisories resolved,
override compatibility/removal conditions, actual verification and limitations.
Retain and report ANY-802/804 findings, including the currently exclusive
shadcn > MCP > AJV > fast-uri path. Their eventual combined state needs a fresh
lockfile/audit/CI run and is not proven by this branch.

## Execution record

Initial audit: 42 High and 6 Critical globally. Provisional installed-tree lint,
boundaries, types, API freshness, 55 test files / 409 tests and Vite build passed
on Node 24.19.0; installed tree differed from lockfile. Docker Linux engine was
unavailable. Frozen Node 22 baseline and final results follow below.

Group 1: PostCSS 8.5.32 resolved through existing parent ranges; pnpm also selected nanoid 3.3.20 and source-map-js 1.2.2 for its children. Retained Next's exact PostCSS 8.5.23. Shared shadcn PostCSS and Next PostCSS children incidentally receive the same safe patch resolutions. Sharp/Next and unrelated children preserved using temporary resolution constraints removed before the final generated lockfile. Frozen install, 55 files/409 tests and build passed on Node 22.23.4; CSS SHA256 A71B7FAC87ED6287D55CA562856932DA6F33E2F6DFBD6EDE26FE0FCA9A1F2BCF unchanged. No persistent override added.

Group 2: refreshed remaining css-tree > source-map-js 1.2.1 to 1.2.2; Tailwind node and PostCSS paths were already fixed by group 1. Temporary compatible resolution constraint removed before normal pnpm lockfile generation. Frozen install, 55 files/409 tests and production build passed; CSS output unchanged. No permanent override.

Group 3: jsdom retained at 30.1.1, undici refreshed within its declared range from 8.11.2 to 8.12.3. Temporary resolution constraint removed; no permanent override. Node engine requirement aligned with existing jsdom (^22.22.2 || ^24.15.0 || >=26.0.0); tested Node 22.23.4. Frozen install and all 55 files/409 tests passed.

Group 4: ESLint 9.39.5 and typescript-eslint 8.67.0 retained. Compatible brace-expansion 1.1.21/5.0.12 selected independently (2.1.7 unchanged); ESLint eslintrc > js-yaml 4.3.2. pnpm also deduplicated shadcn > cosmiconfig onto the same compatible js-yaml 4.3.2, an incidental shared fix rather than ANY-804 implementation. No permanent overrides. Frozen install, lint/boundaries, types, API freshness and 55 files/409 tests passed.

Group 5: browserslist 4.29.5 selected within existing Babel/Hooks and shared shadcn ranges, including its required browser-data children. Shared Next browser-data resolutions deduplicated compatibly; Next and Sharp versions remain unchanged. Hooks 7.1.1 is the available current parent and accepts Zod 4, but the previous graph selected vulnerable Zod 3. Added only eslint-plugin-react-hooks@7.1.1>zod=4.6.7; remove when an upgraded parent naturally resolves patched Zod. The plugin already imports zod/v4 and zod-validation-error/v4; both schema error formatting and valid/invalid conditional-Hooks lint probes passed. Other Zod3 consumers preserved. Final clean frozen install, lint/boundaries, typecheck, API freshness, 55 files/409 tests and Vite build passed. HTTP contract gate: 20 passed. Existing chunk-size warning remains.

Group 6: final audit 18 High / 6 Critical (baseline 42 High / 6 Critical), exclusively ANY-802/804 paths. Zero assigned High/Critical remain. fast-uri remains exclusively shadcn > MCP > AJV. Zod3 finding now reports shadcn > zod; Hooks path is patched. Auth/project gateway: 15 auth and 14 project checks passed; generation/draft gateway controlled responses, saved fixtures, PUT/reload/dedup and owner isolation passed before final Hooks tooling group. Full-stack final verification is blocked below; these bounded runs do not establish full application readiness.

Final browser: controlled login, project list/new/edit, request results, draft list and agreement screens exercised. Agreement field edit and draft request autosave survived reload using controlled HTTP responses. No paid calls. Baseline/final JS and CSS hashes are identical (JS BABA82D6910440DD1510DE2D5FF40AB957EB3F8E7BDE71B32996F6B33BAEEA6B; CSS A71B7FAC87ED6287D55CA562856932DA6F33E2F6DFBD6EDE26FE0FCA9A1F2BCF). Screenshots retained locally; no product source or configuration adaptation required. Independent whole-branch review: no actionable findings.

Infrastructure limits: Docker became available during verification. Official Compose frontend build passed at lint-group state, with API and worker images freshly built from this checkout; final Hooks dependency Docker rebuild failed with daemon EOF, followed by missing Docker Linux engine. Full lifecycle harness passed configuration traversal then failed at disposable PostgreSQL startup on missing engine. Fixed-source private-storage rebuild separately failed on empty Go module-cache source files; existing exact-tag fixture was inspected, no cache or volume was removed. Final Docker/full-stack success is not claimed. Heavy logs, revision labels/build arguments and image identities remain in ignored output/any-805. Initial Compose build used the default local image tag; subsequent build used task-specific tags. No unrelated running services were stopped or restarted. Final CI and refreshed Dependabot graph must be checked on the proposed merge; combined ANY-802/804 validation remains a follow-up.
