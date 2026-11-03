# ANY-802 dependency verification — 2026-11-02

Baseline: `03bda2de6afd2dabd90873fb6a9dfc08e7b89a49` (fresh origin/main).
Only implementation changes: frontend/package.json and frontend/pnpm-lock.yaml.

## Dependency evidence

Search across frontend source, configuration and entry points (excluding package manifest and lockfile) found no analytics imports, initialization or tracking usage. The application is React/Vite served by Nginx.

Before: `frontend → @vercel/analytics@1.6.1 → next@16.3.0 → sharp@0.35.3`, confirmed with `corepack pnpm why @vercel/analytics next sharp`.
After `corepack pnpm remove @vercel/analytics` using pnpm 10.34.1: the same why query returns no paths, and no analytics/next/sharp references remain in the lockfile. pnpm generated the lockfile; no manual lock edits. 44 package records removed, none added, no retained package records changed. Removed exclusive dependencies include @next/env, all @next/swc platform packages, all @img/sharp/libvips platform packages, @img/colour, @emnapi/runtime, @swc/helpers, client-only, styled-jsx and Next's postcss@8.5.23. Other consumers retain their PostCSS versions.

## Fresh audit comparison

`corepack pnpm audit --json` before and after (both exit 1 because findings remain).
Counts: critical 6 → 1; high 42 → 38; moderate 49 → 44; low 7 → 6.
These are audit finding counts, not necessarily unique GHSA counts.

Removed advisories:

| Package | Severity | Advisory |
| --- | --- | --- |
| next | critical | GHSA-p293-qw3h-jr36 |
| sharp | high | GHSA-rgj7-g3m4-5g8c |
| next | critical | GHSA-2xp9-vwfh-vxw4 |
| next | critical | GHSA-vcvr-r3jv-pc5j |
| sharp | high | GHSA-wq5f-xc86-pv6w |
| next | moderate | GHSA-3w37-wq28-93x7 |
| next | moderate | GHSA-4jqv-mc3x-m676 |
| next | low | GHSA-39w2-rjm5-chcv |
| next | moderate | GHSA-f87g-xv8r-7p7x |
| next | moderate | GHSA-mcj8-r9mp-w47p |
| next | high | GHSA-cjq9-62q9-8jv4 |
| next | critical | GHSA-2464-fhr4-w9xw |
| next | high | GHSA-p3m5-59mp-jv5r |
| next | moderate | GHSA-h694-7cp9-m8p3 |
| next | critical | GHSA-673q-mjm6-r5xr |

Remaining advisories, grouped by package (outside this removal; no suppressions or unrelated upgrades):

- @hono/node-server: GHSA-frvp-7c67-39w9 (moderate), GHSA-rmxm-3fg6-px4f (moderate)
- @modelcontextprotocol/sdk: GHSA-22jm-h49p-29qw (high), GHSA-46jr-4wx8-v453 (high), GHSA-6prh-2h8m-c8cw (moderate), GHSA-6qxp-vccf-f47h (high), GHSA-f897-62hf-6gxq (high), GHSA-rvq5-wwqv-78pq (moderate)
- @vitest/mocker: GHSA-82fw-gwwq-j7x9 (moderate), GHSA-qxg6-89mg-rqv8 (moderate)
- baseline-browser-mapping: GHSA-w5vr-8v7q-w6rv (moderate)
- body-parser: GHSA-27r3-jxmh-p828 (high), GHSA-v422-hmwv-36x6 (low)
- brace-expansion: GHSA-3jxr-9vmj-r5cp (high), GHSA-6j4f-fj2g-mc7p (high), GHSA-mh99-v99m-4gvg (high), GHSA-q2hr-2g5m-vwhr (moderate), GHSA-qhr7-859c-m2p7 (high), GHSA-rgw5-rvv9-x895 (high)
- browserslist: GHSA-73wf-gq98-2v4g (high), GHSA-c83g-rgw3-j3cx (high)
- deepmerge: GHSA-gcqx-w48m-w2h4 (low)
- fast-uri: GHSA-333x-w4r6-6crp (low), GHSA-4c8g-83qw-93j6 (high), GHSA-7p8r-x3mc-p8w7 (high), GHSA-f65p-4m7j-42xc (high), GHSA-fph4-wmhf-6fwf (high), GHSA-hrr3-gc8f-f4qj (moderate), GHSA-jqff-g426-hqxp (high), GHSA-qw65-cvwx-89v3 (high), GHSA-v2hh-gcrm-f6hx (high), GHSA-w74x-v6f9-j3xg (moderate), GHSA-xhq7-xmqj-769h (low)
- hono: GHSA-54fx-42gc-7vw4 (moderate), GHSA-5r4p-p66f-jhc7 (moderate), GHSA-79qm-7rj5-m7r9 (low), GHSA-8j4g-w8fx-2239 (moderate), GHSA-crvj-82cr-hjcx (moderate), GHSA-f23p-vx2j-j53r (moderate), GHSA-g6gw-c38x-mqfc (moderate), GHSA-gqvv-2mrq-wpjv (moderate), GHSA-hvrm-45r6-mjfj (moderate), GHSA-hxh3-vqpv-xpqv (moderate), GHSA-w62v-xxxg-mg59 (moderate), GHSA-xgm2-5f3f-mvvc (moderate)
- ip-address: GHSA-22jq-vg5j-6vgg (moderate), GHSA-2vr4-cq9g-pvrc (moderate), GHSA-4xrf-jv44-h6hh (moderate), GHSA-h3mg-xc3c-68pw (moderate), GHSA-j6r3-76f7-8jcv (moderate), GHSA-mwp4-54f8-5fhr (high), GHSA-rpw4-54j3-4h4q (moderate), GHSA-rxp7-6hxx-x8q5 (moderate)
- js-yaml: GHSA-2883-xcg3-v3hh (high), GHSA-52cp-r559-cp3m (high), GHSA-5p4m-2wfm-xmqj (high)
- minimatch: GHSA-g3hv-75wg-m249 (moderate)
- nanoid: GHSA-28wg-ghj8-5hjv (high), GHSA-2v37-7h3g-55p8 (high), GHSA-xwg4-73v4-xw9w (high)
- postcss: GHSA-6g55-p6wh-862q (high), GHSA-fxqj-rqcc-2cmp (moderate), GHSA-qx2v-qp2m-jg93 (moderate), GHSA-r28c-9q8g-f849 (high)
- postcss-selector-parser: GHSA-rj75-hqrm-r3gf (moderate), GHSA-w9m9-85wc-3x92 (low)
- proxy-addr: GHSA-jqcg-44mw-7w3h (critical)
- qs: GHSA-4mjr-xmp4-gh2g (moderate), GHSA-6pq8-jhm2-2vcw (moderate), GHSA-x5fp-wj9c-mxmx (moderate)
- source-map-js: GHSA-68fv-2mgg-jv7q (high)
- undici: GHSA-2m5v-pch6-74hx (high), GHSA-4qv8-2p9j-2685 (moderate), GHSA-4w7w-5xrc-9h26 (high), GHSA-55wc-3pg8-jfw6 (moderate), GHSA-9fm3-97px-rjf6 (moderate), GHSA-f72v-6w45-q472 (moderate), GHSA-qrxm-fqhp-jwvm (high), GHSA-xjj6-f33q-929c (high)
- vitest: GHSA-82fw-gwwq-j7x9 (moderate)
- zod: GHSA-mrhx-c7xc-m3w5 (high)

The remaining critical advisory is proxy-addr GHSA-jqcg-44mw-7w3h.

## Validation

Tested source: baseline revision above plus the two dependency-file changes, with unchanged frontend source/configuration and this report. No UI, backend, metrics, overrides or audit suppressions changed.

- pnpm 10.34.1: clean frozen-lockfile installation in the Docker dependencies stage passed (580 installed packages).
- Native lint and typecheck passed; Linux lint and typecheck also passed.
- Production build passed both natively and in Docker; existing >500 kB chunk warning remains.
- `verify_react_proxy.py --image scg-any802-frontend:check`: 23 checks passed against the actual Nginx image, including SPA login/recovery/project routes and API forwarding, using a deterministic disposable upstream.
- From backend with its own environment, `scripts/verify_any641_runtime.py --containers --backend-image scg-any802-backend:check --frontend-image scg-any802-frontend:check`: passed current production-image registration, duplicate rejection and session revocation, plus 11 disposable application checks. No source overlay or paid LLM calls.
- Existing frontend tests cover authentication, project management and request/analysis rendering. No frontend source or appearance changes were needed.

Freshly built images (revision label `03bda2de6afd2dabd90873fb6a9dfc08e7b89a49`):

- Frontend `scg-any802-frontend:check`: `sha256:5bf6492fdd8ce45d317903bd669f1f8645231a103b371a0926ad8dd52abda9b3`, with label `any802.source-changes=frontend-package-and-lock`.
- Backend `scg-any802-backend:check`: `sha256:a4c507ce926bdb7ef0c181c70b3aac683de1030cae94c172dcf12361cb600039` (unchanged backend source).
- Frontend checks builder: `sha256:d2cc690f02bf2373c0131ecab6b6512b3cb6bede6d2452e7118bcb9560eef644`.

Limitations and failed attempts: native default Vitest reported 406 passing tests but exited with a worker error, so that run failed. The first Linux check container lost its Docker connection (unexpected EOF). A backend attempt from root failed its required-working-directory guard; retry with the root Python environment encountered MemoryError. The final backend run used the correct backend working directory/environment and passed. Full end-to-end Compose readiness with both workers, Mailpit and private test storage was not run. Browser visual inspection was not performed; route/proxy and component tests have bounded scope. No existing application database or volumes were reset or deleted. CI is pending at publication.

Additional environment diagnosis: running the suite in the frontend-only builder image is insufficient: tests need sibling backend, ci and contracts fixtures plus the Python proof driver. That run finished with 49 passing files and six failed files caused by missing resources (ENOENT and unavailable Python driver), not changed assertions. The native threads-pool retry was cancelled after making no progress; no tests were skipped or changed. Final full-suite result is recorded below.

Remaining critical dependency path: `frontend → shadcn → @modelcontextprotocol/sdk → express → proxy-addr@2.0.7`.

Final full-suite verification: `corepack pnpm test --maxWorkers=1` from frontend passed, exit 0: **55 files, 409 tests**, 151.95 seconds. This retains the default forks pool and all tests, reducing concurrency only. `corepack pnpm api:types:check` also passed. The earlier incomplete/failed environment runs above are superseded by this successful full repository run.
