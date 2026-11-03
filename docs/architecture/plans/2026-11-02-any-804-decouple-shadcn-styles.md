# ANY-804: decouple shadcn styles from the CLI

## Goal and checkout

Preserve the complete upstream stylesheet while removing the unused CLI and its dependency chain. Approved base: origin/main at 03bda2de6afd2dabd90873fb6a9dfc08e7b89a49. Branch: codex/any-804-decouple-shadcn-styles. Dedicated checkout: D:/Devpy/ScopeCreepGuard/output/any-804-decouple-shadcn-styles. ANY-802 and ANY-803 checkouts and unrelated reports remain untouched. No task branches are merged.

## Ordered implementation

1. Install with pnpm 10.34.1 and frozen lockfile; capture audit, dependency consumers, build CSS and browser baselines in ignored output/any804.
2. Vendor the entire resolved shadcn stylesheet, its release MIT license and source/checksum provenance. Replace only the CSS import; preserve components.json, tokens and components.
3. Remove shadcn through pnpm; remove the hono override only after its consumers disappear. Regenerate the lockfile without unrelated upgrades.
4. Run clean frozen installation, lint/boundaries, typecheck, tests, API contract check and production build. Repeat audit/tree and browser fixtures at identical viewports; compare compiled CSS and screenshots.
5. Record actual evidence and limitations here; commit scoped files, push and open a main-targeted PR. Do not merge or update Linear status.

## Scope and handoff

No public API changes. No paid model calls. ANY-802 analytics and ANY-805 build/test advisories remain their owners' responsibility. Use only isolated Docker projects and documented startup/migration workflow; never remove existing volumes or stop unrelated services. Heavy evidence and private work logs are not published.

## Verification

Implemented with shadcn 4.10.0. Repository search found only the stylesheet import as application/build usage; the other references were package metadata, component-generation schema and historical documentation. The complete CSS is unchanged (SHA-256 in shadcn.PROVENANCE.md); the MIT release notice is both adjacent to the source and served at /licenses/shadcn.txt. Import order, components.json, tokens and React components are preserved.

Baseline and final installs used pnpm 10.34.1 with --frozen-lockfile. The final installation started with no node_modules (the previous directory was moved into ignored evidence storage). Lockfile regeneration was performed by pnpm: 219 package/version entries removed, none added, retained versions unchanged. Some remaining snapshot entries are reclassified from optional after losing their shared CLI consumer.

Dependency paths before removal:

- shadcn 4.10.0 -> @modelcontextprotocol/sdk 1.29.0 -> express 5.2.1 -> proxy-addr 2.0.7 (also through express-rate-limit).
- shadcn -> MCP SDK -> hono 4.12.25 and @hono/node-server. No other consumer needed the hono override.
- Final clean-install `pnpm why shadcn @modelcontextprotocol/sdk express proxy-addr hono --json` returns `[]`; none remain in the lockfile.

Fresh audit totals (registry-reported findings, not unique advisory counts):

| Severity | Before | After |
| --- | ---: | ---: |
| Critical | 6 | 5 |
| High | 42 | 26 |
| Moderate | 49 | 21 |
| Low | 7 | 1 |

No new advisory IDs appeared. Critical proxy-addr GHSA-jqcg-44mw-7w3h disappears with the CLI path. Removed MCP SDK advisories: GHSA-6qxp-vccf-f47h, GHSA-22jm-h49p-29qw, GHSA-46jr-4wx8-v453, GHSA-f897-62hf-6gxq (High); GHSA-6prh-2h8m-c8cw and GHSA-rvq5-wwqv-78pq (Moderate). Other removed CLI-only findings cover body-parser, hono, @hono/node-server, fast-uri, ip-address, qs, postcss-selector-parser, deepmerge and the CLI's js-yaml path.

Remaining paths are outside this task: analytics -> Next/Sharp (ANY-802), and frontend build/test paths through PostCSS/nanoid, ESLint/TypeScript ESLint -> minimatch/brace-expansion and js-yaml, react-hooks -> Babel -> browserslist/baseline-browser-mapping, Tailwind -> source-map-js, Vitest/mocker and jsdom -> undici and openapi tooling -> zod (ANY-805). These remain audited without suppression. Python LLM dependencies remain ANY-803's scope.

Browser verification used intercepted HTTP responses derived from existing draft/analysis fixtures; no model calls were made. At 1440x1000 and 390x844, all 16 before/after full-page screenshot pairs are pixel-identical. Coverage includes login focus/register, project empty/list/form, request analysis/result, reply and agreement tabs/forms, collapsed scope, export dialog with Escape, filter dropdown/form with invalid date range and focus, and mobile agreement/navigation. Pending-submit disabled controls and expanded native select menus were not separately captured; existing interaction tests passed. Only the existing light product theme is exposed (CSS defines dark variants but no dark palette/theme switch); no new theme was invented. Representative agreement and validation screenshots were visually inspected. Screenshots verify frontend rendering, not persistence, real AI or full-stack readiness.

Production CSS is byte-identical before/after: index-zfRH_LBB.css, SHA-256 a71b7fac87ed6287d55ca562856932da6f33e2f6dfbd6ede26fe0fca9a1f2bcf. The existing large JS chunk warning remains.

Docker limitation: the changed frontend image build used SOURCE_REVISION=03bda2de6afd2dabd90873fb6a9dfc08e7b89a49 plus this worktree's source changes. Docker disconnected during dependency installation with an EOF; a subsequent daemon query found no Docker pipe. No image completed, so there are no new image IDs/revision labels and no Docker/full-stack readiness claim. No existing services, databases or volumes were stopped/reset/removed. Repeat Docker verification when the daemon is available.

Raw audits/trees, scripts, comparison screenshots, install/check logs and the failed Docker build log remain ignored under output/any804. Private WORKLOG files are not published. Independent read-only review found no actionable correctness issues.

Final checks: lint plus architectural boundaries (106 modules), typecheck, api:types:check, production build and all 55 test files / 409 tests passed. The initial baseline's Python proof test failed because the fresh worktree lacked its Python environment (408 tests passed); after `uv sync --locked --all-packages --all-groups --python 3.12`, the final complete suite passed. No new tests were added because stylesheet identity and existing behavior coverage directly verify this change.
