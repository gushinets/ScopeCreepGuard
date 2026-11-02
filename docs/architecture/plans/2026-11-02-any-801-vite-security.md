# ANY-801: Vite security update implementation plan

Base: cfa3578e8a3b598637001932519cde1dbfca7f3a (fresh origin/main).
Branch: codex/any-801-vite-security.
Worktree: D:/.codex/worktrees/any-801-vite-security/ScopeCreepGuard.
Workflow: one user-authorized managed worktree; primary ANY-769 checkout untouched.

## Scope and selection

Current Vite 8.2.1, plugin-react resolved 6.1.2, Vitest 4.1.10; package manager pnpm 10.34.1. Native Node v24.19.0. GHSA-587h-7wmj-h5pm affects Vite through 8.2.3; primary advisory lists 8.2.4 and launch-editor 2.14.2 as corrected. Select the smallest stable corrected 8.2 release after official changelog, migration, engine/peer review and actual graph audit. Do not upgrade unrelated packages (ANY-802–805), alter host exposure, or weaken origin validation.

Sources: https://github.com/advisories/GHSA-587h-7wmj-h5pm ; https://vite.dev/guide/migration ; https://github.com/vitejs/vite/blob/main/packages/vite/CHANGELOG.md .

## Ordered implementation

- [x] Capture full pre-update audit JSON and why Vite/launch-editor; classify unrelated findings.
- [x] Review candidate release notes, engines and peers; exactly pin Vite in frontend/package.json and regenerate pnpm-lock.yaml, checking unrelated churn.
- [x] Frozen install; lint/boundaries, typecheck, tests, build, API freshness where feasible; repeat full audit and resolved graph checks.
- [x] Native Windows dev/preview with isolated controlled upstream and ports: page, React/alias, HMR via temporary change restored afterward, cookies/Origin, streaming, unavailable backend, env validation.
- [x] Fresh frontend Docker image with revision label; repository real Nginx proxy verifier and browser static smoke. Runtime remains Nginx only.
- [x] Record evidence, limits and remaining advisories; scoped commit/push, main PR, verify actual head/base and inspect CI. Never merge or change Linear.

## Isolation, resources and rollback

Evidence and temporary scripts live in ignored output/any-801. No copied env/secrets/node_modules, database, workers, provider calls or shared services. Use ephemeral ports and only task-owned processes/containers; no volumes or pruning. Reuse package cache through pinned Corepack without global configuration changes. No Next.js code is changed; this frontend uses Vite and has no installed Next.js documentation. Rollback: revert the scoped commit (manifest and lockfile together), frozen install and rebuild static image. Keep worktree until authorized cleanup after merge.

## Evidence and handoff

Audit conclusions apply only to advisories known at recorded scan time; unavailable checks remain gaps.

## Completed verification (2026-11-02)

Selected **8.2.4**, exactly pinned; one resolved Vite shared by plugin-react 6.1.2, Vitest/mocker 4.1.10. No companion upgrades, overrides or source/config adaptations. Lockfile changes only Vite integrity/version and consumer references plus widened optional devtools peer. Vite engine remains ^20.19.0 || >=22.12.0; native Node 24.19.0 and Docker Node 22 satisfy it. plugin-react supports ^8.0.0, Vitest supports ^6 || ^7 || ^8. No new peer/engine warnings. Existing ignored msw build-script warning unchanged.

Official tagged changelog 8.2.1–8.2.4 reviewed: dev/HMR/CSS fixes, Windows short-name handling, launch-editor update and file-serving corrections. Migration guide concerns major 7→8 migration; this is an 8.2 patch. No deprecated config use requiring adaptation identified. Existing host 0.0.0.0 remains; actual external reachability was not tested. Production remains static Nginx without Vite runtime.

launch-editor is bundled inside Vite (also listed in its LICENSE), not a separate lockfile package: pnpm why launch-editor returns empty before/after. The tagged upstream changelog records bundled launch-editor 2.14.2. No standalone instance to override. Vite's advisory range is therefore the relevant scan boundary.

Audits: pinned pnpm 10.34.1, Node 24.19.0; full dev+production scan at 11:15:07 UTC before and 11:16:33 UTC after. Before: low 8, moderate 53, high 43, critical 6. After: low 7, moderate 49, high 42, critical 6. All six Vite advisories disappeared, including GHSA-587h-7wmj-h5pm; no known High/Critical attributed to resolved Vite in this scan. This is not a vulnerability-free claim. Raw sanitized registry audit JSON and why outputs are ignored under output/any-801.

Checks: frozen install before/after PASS; lint plus boundaries PASS; typecheck PASS; API types freshness PASS; production build PASS (existing chunk-size warning). Frontend suite: 55 files / 409 tests PASS. Initial 408/409 was missing Python fixture environment; rerun used explicit UV_PROJECT_ENVIRONMENT=backend/.venv and PYTHONPATH=backend/src. Minimal test-only Python dependencies installed, no providers/workers. No test was suppressed.

Native Windows: Vite JavaScript API using actual config, ephemeral loopback ports and controlled HTTP upstream; dev and preview page/SPA fallback, React TSX transform, @ alias, /api path, request cookies/Origin, response Set-Cookie, delayed streaming PASS. Temporary main.tsx comment produced HMR full-reload event and was restored byte-for-byte; no HMR edits committed. Dev backend-unavailable JSON 503 PASS; preview retains existing 502 behavior. Invalid protocol/credentials/path/trailing-slash API origins rejected. Env loading uses unchanged loadEnv and synthetic process env, no private env copied. No exploit performed.

Browser: Playwright CLI isolated any801 session loaded native dev login with synthetic 401 upstream and static Nginx login, checked rendered form and stylesheet (1 stylesheet, white background); deep link /login served. Expected auth 401 console response; unavailable-upstream smoke rendered controlled retry screen. Browser and task-owned containers closed; timed native helpers self-terminate. Native HMR verified by protocol event, not visual browser interaction.

Fresh Docker build PASS. Image ID sha256:c29bd56f37ae5581a6004210513806c5fe2211d01edbbc46b98b719a8b5d0ab1; revision label cfa3578e8a3b598637001932519cde1dbfca7f3a-any801-local. Tested source: base revision plus only manifest/lockfile changes described above; plan added afterward. Repository verify_react_proxy.py PASS: 23 checks against real static image and owned deterministic upstream. No Compose stack/database/volume needed. This bounded frontend verification does not assert full application E2E readiness.

Remaining ownership: ANY-802 covers analytics→Next/Sharp; ANY-804 covers shadcn→MCP/Express and its transitives; ANY-805 covers remaining build/test chains (including moderate Vitest/mocker). ANY-803 is Python LLM scope and outside this frontend audit. No unrelated findings changed or suppressed. Full remaining advisory inventory below (registry entries may repeat an ID for separate affected ranges).

| Package | Remaining advisory IDs and severity |
| --- | --- |
| postcss | GHSA-qx2v-qp2m-jg93 (moderate), GHSA-6g55-p6wh-862q (high), GHSA-fxqj-rqcc-2cmp (moderate), GHSA-r28c-9q8g-f849 (high) |
| brace-expansion | GHSA-3jxr-9vmj-r5cp (high), GHSA-mh99-v99m-4gvg (high), GHSA-rgw5-rvv9-x895 (high), GHSA-q2hr-2g5m-vwhr (moderate), GHSA-q2hr-2g5m-vwhr (moderate), GHSA-qhr7-859c-m2p7 (high), GHSA-qhr7-859c-m2p7 (high), GHSA-6j4f-fj2g-mc7p (high), GHSA-6j4f-fj2g-mc7p (high) |
| js-yaml | GHSA-52cp-r559-cp3m (high), GHSA-5p4m-2wfm-xmqj (high), GHSA-2883-xcg3-v3hh (high) |
| body-parser | GHSA-v422-hmwv-36x6 (low), GHSA-27r3-jxmh-p828 (high) |
| hono | GHSA-xgm2-5f3f-mvvc (moderate), GHSA-hvrm-45r6-mjfj (moderate), GHSA-w62v-xxxg-mg59 (moderate), GHSA-8j4g-w8fx-2239 (moderate), GHSA-f23p-vx2j-j53r (moderate), GHSA-79qm-7rj5-m7r9 (low), GHSA-54fx-42gc-7vw4 (moderate), GHSA-gqvv-2mrq-wpjv (moderate), GHSA-g6gw-c38x-mqfc (moderate), GHSA-crvj-82cr-hjcx (moderate), GHSA-hxh3-vqpv-xpqv (moderate), GHSA-5r4p-p66f-jhc7 (moderate) |
| fast-uri | GHSA-v2hh-gcrm-f6hx (high), GHSA-7p8r-x3mc-p8w7 (high), GHSA-f65p-4m7j-42xc (high), GHSA-fph4-wmhf-6fwf (high), GHSA-jqff-g426-hqxp (high), GHSA-4c8g-83qw-93j6 (high), GHSA-qw65-cvwx-89v3 (high), GHSA-hrr3-gc8f-f4qj (moderate), GHSA-w74x-v6f9-j3xg (moderate), GHSA-xhq7-xmqj-769h (low), GHSA-333x-w4r6-6crp (low) |
| ip-address | GHSA-mwp4-54f8-5fhr (high), GHSA-4xrf-jv44-h6hh (moderate), GHSA-22jq-vg5j-6vgg (moderate), GHSA-rpw4-54j3-4h4q (moderate), GHSA-2vr4-cq9g-pvrc (moderate), GHSA-j6r3-76f7-8jcv (moderate), GHSA-h3mg-xc3c-68pw (moderate), GHSA-rxp7-6hxx-x8q5 (moderate) |
| nanoid | GHSA-28wg-ghj8-5hjv (high), GHSA-2v37-7h3g-55p8 (high), GHSA-xwg4-73v4-xw9w (high) |
| @hono/node-server | GHSA-frvp-7c67-39w9 (moderate), GHSA-rmxm-3fg6-px4f (moderate) |
| postcss-selector-parser | GHSA-w9m9-85wc-3x92 (low), GHSA-rj75-hqrm-r3gf (moderate) |
| browserslist | GHSA-c83g-rgw3-j3cx (high), GHSA-73wf-gq98-2v4g (high) |
| qs | GHSA-x5fp-wj9c-mxmx (moderate), GHSA-4mjr-xmp4-gh2g (moderate), GHSA-6pq8-jhm2-2vcw (moderate) |
| next | GHSA-p293-qw3h-jr36 (critical), GHSA-2xp9-vwfh-vxw4 (critical), GHSA-vcvr-r3jv-pc5j (critical), GHSA-3w37-wq28-93x7 (moderate), GHSA-4jqv-mc3x-m676 (moderate), GHSA-39w2-rjm5-chcv (low), GHSA-f87g-xv8r-7p7x (moderate), GHSA-mcj8-r9mp-w47p (moderate), GHSA-cjq9-62q9-8jv4 (high), GHSA-2464-fhr4-w9xw (critical), GHSA-p3m5-59mp-jv5r (high), GHSA-h694-7cp9-m8p3 (moderate), GHSA-673q-mjm6-r5xr (critical) |
| vitest | GHSA-82fw-gwwq-j7x9 (moderate) |
| @vitest/mocker | GHSA-82fw-gwwq-j7x9 (moderate), GHSA-qxg6-89mg-rqv8 (moderate) |
| baseline-browser-mapping | GHSA-w5vr-8v7q-w6rv (moderate) |
| sharp | GHSA-rgj7-g3m4-5g8c (high), GHSA-wq5f-xc86-pv6w (high) |
| source-map-js | GHSA-68fv-2mgg-jv7q (high) |
| proxy-addr | GHSA-jqcg-44mw-7w3h (critical) |
| @modelcontextprotocol/sdk | GHSA-6qxp-vccf-f47h (high), GHSA-22jm-h49p-29qw (high), GHSA-6prh-2h8m-c8cw (moderate), GHSA-46jr-4wx8-v453 (high), GHSA-rvq5-wwqv-78pq (moderate), GHSA-f897-62hf-6gxq (high) |
| zod | GHSA-mrhx-c7xc-m3w5 (high) |
| undici | GHSA-4qv8-2p9j-2685 (moderate), GHSA-f72v-6w45-q472 (moderate), GHSA-xjj6-f33q-929c (high), GHSA-4w7w-5xrc-9h26 (high), GHSA-2m5v-pch6-74hx (high), GHSA-qrxm-fqhp-jwvm (high), GHSA-9fm3-97px-rjf6 (moderate), GHSA-55wc-3pg8-jfw6 (moderate) |
| deepmerge | GHSA-gcqx-w48m-w2h4 (low) |
| minimatch | GHSA-g3hv-75wg-m249 (moderate) |

Delivery: implementation commit d71ac84c84b10a3ff1e63b377782c7ed75fd674e pushed; PR https://github.com/gushinets/ScopeCreepGuard/pull/61 verified with actual head codex/any-801-vite-security and base main at cfa3578e8a3b598637001932519cde1dbfca7f3a. Initial published-head CI run 41436758280 inspected: rebase and compose-minimum passed, backend/frontend/containers in progress. Final CI status is reported at handoff; pending jobs are not claimed passed. This documentation-only follow-up does not change tested frontend source. No merge or Linear mutation.

