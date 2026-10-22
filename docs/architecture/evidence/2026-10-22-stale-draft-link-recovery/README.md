# Stale draft link recovery

## Cause and changes

Local logs showed a new registration followed by two correctly rejected lookups of the prior account's draft (current and legacy endpoints both returned 404). Workspace startup treated the second 404 as a fatal application error. The original draft still exists in PostgreSQL; it was not deleted.

The Drafts feature now resolves current and legacy links in one place. A confirmed unavailable link falls back to the signed-in user's first active draft or empty workspace. The stale `draft` parameter is replaced/removed while other query parameters, the hash, and router state are preserved. Later unavailable links retain the current saved draft. Server/network failures still surface as failures; backend ownership checks are unchanged.

Logs also confirmed separate `errors.providerBudgetUnavailable` failures for checks and agreement preparation. The pinned LiteLLM catalog lacks GPT-6 Luna pricing. The ignored local Compose overlay now sets the existing rate-bound options to USD 0.0000001/input token and USD 0.0000005/output token, from [the official model documentation](https://developers.openai.com/api/docs/models/gpt-6-luna), checked on 2026-10-22. Both API and worker keep `gpt-6-luna`; the USD 1.00 operation ceiling is unchanged. No backend pricing algorithm or user commercial terms changed.

## Verification

- Docker: 57 tests passed across persistent-navigation (24), persistent-store (31), and workspace-outage (2). New regressions cover empty/existing accounts with an unavailable link, current/legacy server errors, and later unavailable navigation. Existing legacy snapshot tests pass.
- Docker production build and TypeScript checks passed; lint and feature boundaries passed (98 modules); `git diff --check` passed.
- Browser at localhost:3000: registered an owner account and project, then registered separate new accounts through the actual registration form with the owner's draft in `returnTo`. Verified recovery to the empty workspace, URL cleanup, reload, and backend 404 isolation. After creating each account's own project, verified that the same stale link opens that account's own draft. Passed in Russian and English.
- API and worker policy were inspected locally: selected model `gpt-6-luna`, required rate metadata present, worst-case two-call admission estimate below the unchanged cost ceiling. Services are running and API/frontend/database health checks pass.
- [Russian recovered workspace](stale-link-recovered-ru.png), [English recovered workspace](stale-link-recovered-en.png), [browser reproduction](browser-journey.js).

No paid AI calls were made, so live generation/provider access is not asserted. No data was removed or moved between accounts. Existing project changes remain uncommitted on `codex/design-onboarding`; no push or PR.
