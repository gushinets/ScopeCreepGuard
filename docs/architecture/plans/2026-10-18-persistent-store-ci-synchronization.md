# Persistent-store CI synchronization

Base: `b095af4` on `codex/scope-assessment-and-metrics-completion`, existing
checkout. Preserve all unrelated untracked architecture/evidence/design files.
No worktree, reset, stash, commit, push, PR or data changes.

Scope: fix the intermittent `persistent-store.test.tsx` reopening regression
test. The provided CI log fails at the initial saved-term assertion; local
baseline fails at the corresponding reopened assertion (24 passed, 1 failed).
The DOM is committed before renderHook's passive effect publishes result.current.
Production projects, drafts and assessment behavior are outside this repair.

1. Read installed Next.js guides and trace rendering/hook publication.
2. Wait on the two saved-term assertions themselves, retaining their expected
   values, original assessment, cleared fields, free-work, immutable snapshot
   and no-auto-generation assertions. No sleeps or timeout increases.
3. Run the focused file and the full disposable frontend/HTTP-contract harness;
   lint/type-check changes. Record evidence, limitations and local handoff in
   ignored journals. No application rebuild is necessary for a test-only repair.

Evidence: `output/ci-persistent-store/`. Owner: current chat. Full harness must
use disposable PostgreSQL and synthetic accounts, without paid AI calls.

## Result

- RED: unmodified focused file failed locally at the reopened saved-term
  assertion (1 failed /24 passed), corresponding to the initial saved-term
  assertion in the supplied CI log. `baseline.log` retains this evidence.
- GREEN: both assertions now use Testing Library `waitFor`, without changing
  expected values or timeout settings. All25 tests in the file pass;
  `focused-green.log`, exit0. No production code changed.
- Changed-file ESLint and full TypeScript check pass, exit0. The initial
  TypeScript run exhausted its256MB heap (exit134); the512MB bounded rerun
  completed cleanly (`typecheck-r2.log`, exit0). Diff whitespace check passes.
  Installed Next.js client and server component guides read.
- The real `check-gateways.mjs --suite frontend` harness was attempted with
  local `VITEST_MAX_WORKERS=2`. It failed before tests: disposable PostgreSQL
  docker-run exit125; Docker Desktop reports unable to start. PowerShell also
  reported out of memory. Host free virtual memory was approximately0.9GB.
  `full-frontend.log` and exit1 retained. Full-suite PASS is not claimed.
- No unrelated processes stopped; no application data/configuration changes,
  image rebuild, paid AI call, commit, push, PR or Linear update. Untracked
  documents/evidence preserved; AGENT.md and WORKLOG.md remain ignored.

## Related backend CI failure (second supplied log)

CI reports806 passed /1 failed: test_llm_worker publication test `[head]`
expects operations_succeeded6, including agreement preparation. The source
requirement explicitly includes only four operation kinds; correct fixture
total is2 checks +1 regeneration +1 translation +1 estimate =5. Existing
production filtering already implements that rule. Repair the stale integration
assertion, assert that the succeeded agreement still exists in the operation
ledger, and verify five aggregate duration samples. Extend the existing formula
regression across succeeded/failed/cancelled preparation. Run focused unit/static
checks and attempt the isolated PostgreSQL test, reporting Docker availability
honestly. Preserve the frontend synchronization fix; no product or database edits.

Backend result: corrected total5 and duration sample5, plus a raw-ledger
assertion for one succeeded agreement. All15 formula tests pass (previous13,
now succeeded/failed/cancelled agreement cases). Changed-file Ruff lint and
format checks pass. Focused worker integration attempt fails in setup for both
parameters: Docker disposable database exit125, before exercising the test;
`output/ci-backend-metrics/worker-integration.log`, exit1. Thus no fresh
PostgreSQL/full-backend PASS is claimed. The supplied CI's806 passes establish
only that earlier CI run, not local validation after this correction.

## Publication authorization

The user subsequently authorized committing and pushing these CI fixes.
Publish the three changed test files and this implementation record to the
existing `codex/scope-assessment-and-metrics-completion` branch. Fetch confirmed
local HEAD and the remote branch both at `b095af4` before publication. Preserve
all other untracked documents/evidence; keep AGENT.md and WORKLOG.md ignored.
