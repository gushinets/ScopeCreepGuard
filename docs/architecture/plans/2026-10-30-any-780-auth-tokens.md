# ANY-780 authentication foundations

Base: origin/codex/any-758-email-verification-password-reset at 2c920e1.
Branch: codex/any-780-auth-tokens. Isolated managed worktree; no commit/push/PR.
Specification: agreed ANY-780 design in the task request.

- [x] Add revision 0009, authoritative catalog and user transition defaults.
- [x] Implement hash-only token repository and complete transaction services.
- [x] Bind signed sessions to database session_version across API dependencies.
- [x] Verify expiry, rollback, concurrency, duplicate registration and migration preservation.
- [x] Run formatting, typing, catalog and security diff review; record evidence.

No HTTP flows, frontend, email transport, or startup DDL. ANY-779 is not merged
and is not a dependency of these internal services. ANY-781/782 own public flows.

Policy: every issuance/application/revocation locks users first, then tokens.
Reset hashing happens before locks. Issuance linearizes when the user lock is
acquired: issuance before reset is revoked; issuance after reset is a new request.
Legacy accounts retain NULL verification evidence and are exempt from future
verification enforcement; new accounts require it. Missing signed session claim
means version zero, malformed present values fail closed.

Verification limitation at start: Docker daemon unavailable.

## Implementation and handoff

Implemented 0009_auth_tokens, its frozen catalog, current Core schema selection and
UserRow auth columns; historical catalogs remain unchanged. AuthTokenService and
AuthTokens repository provide issuance/inspection/revocation and atomic application.
Domain token values/ports keep service logic independent of database implementations.
AuthService register/login issue signed generations and me compares the actual row.
No public security fields or HTTP routes were added. Service interface documentation:
backend/src/scope_guard/services/auth/README.md.

Auth tests now explicitly request Alembic head: support.prepare_alembic retains its
historical baseline default for unrelated fixtures. Current profiles prevent owner
deletion; the missing-owner auth test uses a signed absent UUID instead of deleting
an owner with a profile. Token FK also restricts owner deletion. Concurrent
registration now uses different passwords and proves the loser gets no cookie and
cannot change the winning hash. Existing duplicate-registration status remains 409.

## Verification evidence (2026-10-30, Europe/Moscow)

Revision: 2c920e194d844ae61b37fbc79fb78c5d7e94cf8d plus uncommitted ANY-780 source.
Base refreshed from origin before creating codex/any-780-auth-tokens in managed
worktree D:/.codex/worktrees/any-780-auth-tokens/ScopeCreepGuard.
Integration contains Compose/CI fix 2c920e1; SMTP ANY-779 remains open PR #48 and was
not imported. Target PR base remains codex/any-758-email-verification-password-reset.
No commit, push, PR, merge, or Linear change performed. Original checkout/branch and
untracked ANY-778 dependency report are preserved.

Commands below use D:/Devpy/ScopeCreepGuard/.venv/Scripts/python.exe (python),
ruff.exe and mypy.exe from that same existing environment. Source PYTHONPATH points
to this worktree, not the original checkout. The ignored frontend/node_modules
junction reuses original dependencies for the frozen Node compatibility test.

From repository root:

```powershell
$env:PYTHONPATH='backend/src;apps/api/src'
python -m pytest backend/tests/unit/test_session_versions.py backend/tests/unit/test_auth_use_cases.py backend/tests/api/test_auth.py -q
python -m pytest backend/tests/unit -q --ignore=backend/tests/unit/test_auth_adapters.py
python -m pytest backend/tests/unit/test_auth_adapters.py backend/tests/unit/test_openapi_export.py backend/tests/unit/test_technical_operations.py --basetemp output/any780-temp-verify -q --tb=short
mypy backend/src apps/api/src --cache-dir output/any780-mypy
git diff --check
```

Results: targeted auth 27 passed. Broad unit 750 passed with 6 Windows Temp
permission errors; the affected files plus JOSE/bcrypt compatibility passed in the
separate fresh-temp run (17 passed). No single all-green broad-suite run is claimed.
Mypy passed 235 source files. Ruff lint passed for every changed Python file;
ruff format --check passed 23 files after formatting current workflow.py. Diff check
passed. New malformed-generation tests were observed failing (9) before implementation,
then passing (9). Password/JOSE compatibility retains legacy fixture verification
and asserts the new session claims, rather than requiring unchanged signed bytes.

From backend (PYTHONPATH=src;../apps/api/src):

```powershell
python -m pytest tests/integration/test_auth_tokens.py tests/integration/test_auth_workflows.py --require-integration -q --tb=short
python -m pytest tests/integration/test_auth_tokens.py -k 'token_transactions or repeat_registration' --require-integration -q --tb=short
```

Final full targeted PostgreSQL run: 7 passed in 30.75s. Subsequently added log-secret
and duplicate-token-state assertions: 3 passed, 3 deselected in 18.36s. These tests
use owned disposable PostgreSQL containers and unique databases. Covered both
purposes, hash-only persistence, exact lifetime/expiry boundary, wrong user/purpose,
revocation/used states, rollback of hash/version/token, expiry during hashing,
same-token application, different reset links, issuance before and after reset,
missing user, legacy/new defaults and migration preservation of users/profiles/projects.
Protected routes /api/auth/me, /api/v2/projects and /api/v2/profile reject both old
versioned and genuinely claim-less sessions after reset; sign-in works with the
new password/version. Malformed signed claims are covered by unit tests.

Review by a read-only security reviewer found one startup verifier dispatch bug;
fixed 0009 dispatch in verify_nonblocking_schema and added real catalog coverage.
Reviewer found no further concrete security/atomicity bugs. Its three suggested
race/expiry/rollback checks were added and passed. An intermediate run/build lost
Docker engine connectivity; sequential reruns passed and the final build succeeded.

## Compose gate and images

No production databases, existing volumes, real SMTP, or paid LLM calls used.
Initial project scg-any780-20261030 used port 55880; final gate project
scg-any780-gate-20261030 used port 55881. Both are task-specific and retain volumes.
No prune, volume deletion, or database reset was performed by task commands.
The existing integration harness cleans only databases/containers it creates.

Final build:

```powershell
docker build -f apps/api/Dockerfile --target runner --build-arg SOURCE_REVISION=2c920e1 -t scg-any780-api:verification .
docker image inspect scg-any780-api:verification --format '{{.Id}} {{index .Config.Labels "org.opencontainers.image.revision"}}'
```

Fresh API image ID: sha256:2b5883d10eaa07fde4f9d66a38c8863fe7b7bf5c75380c3fa8ce4c4d13a6ae78.
Revision label: 2c920e1 (base revision plus local source, not a committed ANY-780 revision).
PostgreSQL image ID: sha256:266d3c257594e195b309ae9d1805e54c788f1d7b375f56bf6c367aac6c917e7b.

Gate environment (all synthetic):

```powershell
$env:POSTGRES_PORT='55881'
$env:POSTGRES_PASSWORD='any780-synthetic-local'
$env:SCOPE_GUARD_API_IMAGE='scg-any780-api:verification'
$env:OPENAI_API_KEY='synthetic-no-calls'
$env:AUTH_SECRET='synthetic'
$env:SCOPE_GUARD_OPENAI_MODEL='synthetic'
$env:SCOPE_GUARD_LLM_INPUT_RATE_BOUND='0'
$env:SCOPE_GUARD_LLM_OUTPUT_RATE_BOUND='0'
$env:SCOPE_GUARD_EXPORT_BUCKET='synthetic-private'
docker compose -p scg-any780-gate-20261030 -f deploy/compose.postgres.yaml up -d
$env:SCOPE_GUARD_DATABASE_URL='postgres://scopeguard:any780-synthetic-local@postgres:5432/any780_upgrade_final'
docker compose -p scg-any780-gate-20261030 -f deploy/compose.backend.yaml run --rm migrate
$env:SCOPE_GUARD_DATABASE_URL='postgres://scopeguard:any780-synthetic-local@postgres:5432/any780_fresh_final'
docker compose -p scg-any780-gate-20261030 -f deploy/compose.backend.yaml run --rm migrate
```

Both named databases were explicitly created empty in this disposable project.
Upgrade fixture was prepared through migrate(target='0008_contextual_onboarding')
with a synthetic user/hash, profile and project (same pattern as the committed
upgrade test), then the final image gate upgraded it. Upgrade gate exit 0,
execution_id=96f10bc9c2c748ffb8cf7ce4d2ef5c89; fresh gate exit 0,
execution_id=7b893f782d7c421e88c9612b71b8d1f7. Exact catalog validation passed.
Post-upgrade SQL returned email_verified_at IS NULL=true,
email_verification_required=false, session_version=0, preserved hash=true,
profiles count=1 and projects count=1. Re-running the gate at head was a successful noop.

Scope of verification is backend/database components only. Full application E2E,
frontend, both worker processes, Mailpit and private object storage were not started
as a full stack; no full readiness or external-email-delivery claim is made.
ANY-781/ANY-782 must connect these services to public flows and access policy;
ANY-779 must supply email preparation/transport. Keep raw tokens out of logs and
public response contracts when integrating those flows.


## Historical-schema regression investigation and correction (2026-10-30)

This section supersedes the earlier description of UserRow as a current auth
mapping. The earlier image verification predates this correction; those images
must not be represented as containing the corrected repository. No new images,
worktrees or environments were created for this investigation.

Reproduced before changing code, from backend with the existing environment:

```powershell
$env:PYTHONPATH='src;../apps/api/src'
D:/Devpy/ScopeCreepGuard/.venv/Scripts/python.exe -m pytest tests/integration/test_database_models.py -x -q --tb=short --require-integration
```

Result: 1 failed. test_mapped_rows_round_trip_decimals_json_and_server_defaults
failed at session.flush() in test_database_models.py with
psycopg.errors.UndefinedColumn: column "email_verified_at" of relation "users"
does not exist. The emitted INSERT included email_verified_at and RETURNING
session_version/email_verification_required against intentionally selected 0001.
The earlier current-head migration gate did not cover this compatibility case.

Root cause: current security columns were added to the deliberately historical
ORM mapping shared with baseline project/history/draft mappings. Several historical
HTTP workflow tests also used current auth on pre-0009 schemas. Raising all fixtures
to head would retire/alter the structures those tests are supposed to exercise.

Correction:

- Restored models/users.py to its frozen four-column baseline UserRow. Added an
  explicit column-set regression assertion in test_database_models.py.
- Current repositories/users.py now uses the separate authoritative Core users
  mapping from WORKFLOW_METADATA (0009), including session_version. It has no
  schema detection, missing-column suppression or version-zero database fallback.
  INSERT remains insert-only with the same PostgreSQL duplicate-email constraint.
- Added tests/integration/historical_auth.py, a test-only baseline ORM auth adapter
  and UoW, plus an opt-in historical_auth fixture. It is never selected by runtime
  composition. Historical sessions explicitly use the former version-zero contract.
- Opted in baseline project/draft/generation/document/remaining workflow modules
  and the 0004 saved-fixture HTTP workflow. Their migration targets are unchanged.
- Current auth workflow assertions use the current Core table. Token/session and
  current auth tests continue to use real production repositories against head.

Audit: all direct UserRow consumers now belong to baseline model/rollback tests or
the test-only historical adapter. All direct current Users/AuthUnitOfWork consumers
use head, including token tests, profile activity, marketing, onboarding and generation
cancellation. Marketing's explicit 0005 unavailability test does not call Users.
Other head workflows and migration-specific SQL fixtures require no fixture changes.
The prepare_alembic default remains 0001. No migration, manifest, schema validator,
startup behavior or migration gate was changed by this correction.

Tests actually executed after correction, from backend with the same PYTHONPATH
and D:/Devpy/ScopeCreepGuard/.venv/Scripts/python.exe:

```powershell
python -m pytest tests/integration/test_database_models.py tests/integration/test_service_rollback.py tests/integration/test_project_workflows.py tests/integration/test_draft_workflows.py tests/integration/test_generation_workflows.py tests/integration/test_document_workflows.py tests/integration/test_remaining_workflows.py tests/integration/test_auth_tokens.py tests/integration/test_auth_workflows.py --require-integration -q --tb=short
python -m pytest tests/integration/test_persistent_workflow.py --require-integration -q --tb=short
python -m pytest tests/integration/test_alembic_baseline.py tests/integration/test_readiness_and_constraints.py tests/integration/test_unit_of_work.py tests/unit/test_database_metadata.py tests/unit/test_auth_adapters.py tests/unit/test_session_versions.py tests/unit/test_auth_use_cases.py --require-integration -q --tb=short --basetemp ../output/any780-history-check-temp
```

Results respectively: 18 passed (66.02s), 11 passed (55.98s), 48 passed (39.47s).
New token/concurrency/rollback/session/duplicate-registration tests passed using
the current Core repository. Existing harness used owned disposable PostgreSQL
containers/databases with the already available image; no application images were
built and no existing database/volume was reset or removed.

From root, mypy repositories/users.py --follow-imports=silent passed (1 source file).
Ruff check on all changed/new Python files passed; format --check passed 26 files.
git diff --check passed. Reviewed the additional diff for unrelated changes/secrets.
Git revision remains 2c920e194d844ae61b37fbc79fb78c5d7e94cf8d plus local ANY-780
source and this correction; no commit, push, PR, Linear update or merge performed.
Full repository test suite and fresh image/full-stack E2E were not run for this
correction. Earlier image evidence applies only to the earlier source state.


## Publication authorization

The user subsequently authorized creating the PR. Publish this task branch only,
targeting codex/any-758-email-verification-password-reset. Prior no-commit/push
statements above describe the verification stages before that authorization.
Remote base was fetched again and remained 2c920e1; the proposed merged source
therefore matches the source verified during the historical regression correction.
No image rebuild or environment setup is part of publication.


## PR #50 backend CI correction

The supplied Linux CI log at head d4fd66d reported 1007 passed and one failure:
test_previous_release_upgrade_preserves_rows_and_refuses_downgrade. Reproduced
locally before editing: 1 failed, 1 passed in test_release_migration.py. The test
compared whole user JSON against the pre-0009 shape, so the three intended new
legacy fields caused the mismatch despite preservation of every existing value.

Updated only the expected user snapshot with session_version=0,
email_verified_at=None and email_verification_required=False. Full-row equality
remains strict; projects/drafts/history comparisons and downgrade/noop checks
remain unchanged. No migration or production code changes.

From backend with the existing Python environment and PYTHONPATH=src;../apps/api/src:
python -m pytest tests/integration/test_release_migration.py tests/integration/test_auth_tokens.py tests/integration/test_auth_workflows.py --require-integration -q --tb=short
Result: 9 passed in 63.73s. Ruff check backend apps/api passed; Ruff format --check
backend apps/api passed (395 files); git diff --check passed. No image builds.

The original PR head also has separate frontend and containers failures:
verify_any640_auth_gateway.py:92 and verify_any641_runtime.py:132 fail registration.
Both scripts prepare the historical baseline but invoke current auth; the existing
pytest historical_auth fixture does not apply to those subprocess/image entrypoints.
Those acceptance-script failures are not resolved by this backend test correction.
Do not claim all PR checks green; they need a deliberate historical/current-schema
separation without introducing a production missing-column fallback.


## PR #50 complete gateway/container CI investigation

At head 2fcf9d0 backend, rebase and compose-minimum checks succeeded. Frontend
and containers still failed baseline registration. The previous section's unresolved
acceptance failures are addressed by the changes below. Runtime auth remains strict.

- The test-only HTTP entrypoint now supports explicit SCG_HISTORICAL_AUTH=1;
  historical ANY-640 gateway runners select it together with baseline migration.
  The flag is read only in tests/http_auth_app.py, never in production settings.
- The historical container document journey explicitly loads a mounted, read-only
  test ASGI factory with the baseline adapter. All original 11 PDF/extraction
  checks remain. The fixture is not included in the production image.
- Before that historical journey, the container runner prepares a separate current
  head database and launches the image's ordinary production entrypoint. It proves
  new-account defaults, successful registration, duplicate-password rejection,
  database session-version revocation on me/projects, and login with the original
  password. No historical adapter or SCG flag is passed to that process.
- Optional --source-tree allows local reuse of an existing image's dependencies
  with explicit read-only Python source mounts. CI omits the flag and checks its
  fresh image. Output reports sourceOverlay to prevent confusing the two modes.

Local verification used the existing Python environment, cached PostgreSQL image,
existing frontend dependencies and existing application images; no image builds or
new environments/worktrees. pnpm through root corepack selected incompatible v11;
used the existing Vite executable directly instead, with no lockfile changes.

Commands from frontend: node node_modules/vite/bin/vite.js build (passed).
From backend, PYTHONPATH=src;../apps/api/src and the existing Python executable:

```powershell
python scripts/verify_any640_auth_gateway.py
python scripts/verify_any640_generation_gateway.py
python scripts/verify_any640_drafts_gateway.py
python scripts/verify_any641_runtime.py
python scripts/verify_any641_runtime.py --containers --backend-image scg-any780-api:verification --frontend-image scope-guard-frontend:local --source-tree
```

All five commands exited 0. Auth/project gateway assertions passed in all three
variants, retired generation used the deterministic fixture with no paid calls,
and host/container document journeys both passed 11 checks. Container current
production auth assertions passed separately before the historical journey.

Existing backend image ID: sha256:2b5883d10eaa07fde4f9d66a38c8863fe7b7bf5c75380c3fa8ce4c4d13a6ae78; revision label 2c920e1.
Existing frontend image ID: sha256:d05d75dbe59ddb441d231a83d32de9940314f3741f62c7b1badc1c41c59de607; revision label 1209177.
The local run includes uncommitted Python source changes over 2fcf9d0 and reports
sourceOverlay=true; it does not claim these old image layers contain the new source.
Only owned temporary harness resources were cleaned; no existing databases reset,
no volumes removed, no prune. No full-stack E2E or external-email claim.

Ruff check backend apps/api passed; Ruff format --check passed 396 Python files.
The updated PR must also pass fresh remote checks before claiming all CI green.


### Full Compose smoke revision expectations

On 2b434c1, both frontend CI runs passed, including all gateway variants. The
containers job passed image-level auth/documents/proxy checks, then reached full
Compose smoke and exposed a hard-coded head assertion in verify_docker_startup.py:543
expecting 0008_contextual_onboarding. Its later concurrent-migrator assertion also
expected the second process to start from 0008. Updated the explicit head to
0009_auth_tokens and made the serialized second-process assertion use that checked
head. Historical seed target 0007 and all concurrency/noop/data-preservation checks
remain unchanged. A search of backend/scripts and ci found no other 0008 assertions.

Local verification (no new image builds): verify_docker_startup.py --config-only
passed root/deploy parity, dependency closures, isolation and gate configuration on
Compose 5.6.0. test_release_migration.py plus test_stack_update.py: 13 passed in
16.18s. Ruff lint/format and diff checks passed. Full image/full-stack execution
is delegated to the fresh remote CI run; no local full-stack readiness claim.
