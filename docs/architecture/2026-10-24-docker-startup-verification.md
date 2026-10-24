# Docker startup and migration verification

24 October 2026, Europe/Moscow. Infrastructure verification only; no live deployment.

## Provenance and preservation

- Base: freshly fetched `origin/main`, `0bea6bc8c2e106f78dd2a14cbff4cb0b7e4c3d90`.
  A final fetch confirmed main had not advanced.
- Branch: `codex/predictable-docker-startup`.
- Final runtime/configuration revision: **`2e6167d7edbcfbc246a398e72a72f770330f7b78`**.
  Tracked sources were clean during final verification. A later documentation-only
  commit records this report; it does not change tested runtime sources.
- Installed Compose: **5.6.0**; minimum **2.24.0** tested with official,
  checksum-verified standalone executables. Linux configuration was additionally
  checked on **2.24.7**. Docker Desktop 4.95.0 / Linux Engine 29.8.2 on Windows.
- Actual packaged Alembic head: **`0008_contextual_onboarding`**. The runner resolves
  the single packaged head; no feature overlay or release-test target override exists.
- Existing untracked nine-issue acceptance report, plan and evidence were preserved
  and excluded from commits. Existing developer database volumes were not mounted,
  migrated, reset or deleted. Tests used UUID `scg-startup-test-*` projects and
  exclusively owned PostgreSQL containers/databases/volumes.

Final images were built from the tested revision and carry its
`org.opencontainers.image.revision` label:

| Image | Local image ID |
| --- | --- |
| API and migration | `sha256:0362b0369a5e3a2af8d8dd8bc5393a30963fa0f33c5f39ea11973262bbe57358` |
| Both worker roles | `sha256:be02fca9ede7ccbf0293b3b7f3d015f4e351222ab7cc442271528490e7dd352e` |
| Frontend | `sha256:db63fc0fe9ccd3395afd87a840f55b7cd1423c228705de3d53cbe84abd758608` |

## Executed commands and results

Commands below were run from the repository root unless otherwise noted. Python
means the workspace interpreter (`.venv/Scripts/python.exe` on this Windows host).
Fixture credentials were synthetic. Full rendered configurations and private command logs
are deliberately excluded from this report.

```sh
docker build -f apps/api/Dockerfile --target runner --build-arg SOURCE_REVISION=2e6167d7edbcfbc246a398e72a72f770330f7b78 -t scope-guard-api:startup-test .
docker build -f apps/api/Dockerfile --target export-worker --build-arg SOURCE_REVISION=2e6167d7edbcfbc246a398e72a72f770330f7b78 -t scope-guard-worker:startup-test .
docker build --target runner --build-arg SOURCE_REVISION=2e6167d7edbcfbc246a398e72a72f770330f7b78 -t scope-guard-frontend:startup-test frontend
python backend/scripts/verify_docker_startup.py --config-only
python backend/scripts/verify_docker_startup.py --compose-binary output/docker-compose-2.24.0.exe --config-only
python backend/scripts/verify_docker_startup.py --compose-binary output/docker-compose-2.24.0.exe
```

The full harness uses the exact tracked full/component entry points, with synthetic
process settings and empty service env files selected through documented fixture
path variables. It does not rewrite dependencies, services or the release target.
Test-only S3 uses the existing fixed-source `scope-guard-s3-test:release20250422`
fixture. The full-stack command was also executed with **`up --build -d --wait`**,
not solely with prebuilt images; duplicate image references built successfully.

| Required scenario | Result and assertion |
| --- | --- |
| Fresh database в†’ complete stack | PASS on 5.6.0: release head reached; API, frontend and both workers healthy |
| Previous supported schema upgrade | PASS: explicit disposable 0007 fixture upgraded through the release image; existing user retained. PostgreSQL integration test additionally compares users/projects/drafts/history before and after |
| Already current | PASS: exit 0 and `migration_noop` |
| Concurrent migration processes | PASS: two queued runners at 0007; exactly one applies 0008, one reports no-op; source logs show 0007 then committed 0008 after acquisition |
| Migration failure в†’ no fresh dependent startup | PASS: incompatible extra table in disposable DB; migration nonzero, only PostgreSQL running |
| Bounded lock timeout | PASS: held advisory lock, 0.5-second fixture deadline; waiting/timeout/failure logs and exit 1 |
| Migration termination | PASS: temporary Alembic callback pauses after DDL; TERM gives nonzero exit; next runner obtains lock and completes after rollback. Existing integration also tests process death and rollback |
| Each component | PASS: exact expected running-service closure for PostgreSQL, backend, frontend and both workers |
| Component в†’ complete stack | PASS: same PostgreSQL container ID, mount and data volume; canonical service/network/volume configuration equality |
| Existing-stack maintenance | PASS: migration container forced to a new ID despite prior success; no-op rerun; applications recreated only after success; registered account retained |
| Failed existing-stack update | PASS: explicitly stopped old applications remain stopped when forced migration fails |
| Existing-volume transition | PASS on final 5.6.0 matrix: missing external volume refuses startup; mapping the owned existing volume retains account data; normal down/up also preserves it |
| Missing required settings | PASS: missing auth configuration fails; PostgreSQL entry remains independently usable |
| Production/Dokploy configuration | PASS: complete service set and unchanged gates, no published local ports or local service env files, required deployment credentials/origins |
| Frontend/API persistence smoke | PASS: register, onboarding 200, create project, autosave Draft and read confirmed saved content through the actual frontend proxy |
| Paid calls | None submitted. Synthetic provider key only; `provider_calls` count remains zero |

The complete final runtime matrix also **passed on Compose 2.24.0** against the
same revision-labelled images, including external-volume transition and refusal,
concurrent upgrade/recheck and failed-maintenance gating. Compatibility alias
`docker-compose.yml` configuration passed on both 5.6.0 and 2.24.0.

Additional checks:

| Check | Result |
| --- | --- |
| Full backend `pytest --require-integration` with disposable Docker databases | **953 passed**, 627.31s; this run preceded adding the final unexpected-exception redaction case |
| Final Docker backend unit/API/architecture suite with Node/Python interoperability | **806 passed**, 148 integration cases deselected, 73.19s, against committed sources; includes the final redaction case |
| Focused final startup, migration redaction, safety and update-failure tests | **31 passed** |
| Full frontend suite in isolated Linux Node/Python environment | **383 passed**, 52 files, including Python proof interoperability |
| Frontend lint and module boundaries, TypeScript, generated API type freshness | PASS; 100-module boundary check |
| Production frontend/API/worker builds | PASS; successful sequential retries and documented Compose build/start |
| Retained API/frontend container runtime checks | PASS: 11 auth/upload/PDF checks and 20 frontend proxy checks |
| Ruff lint / format | PASS; 387 Python files formatted |
| mypy | PASS; 230 source files |
| OpenAPI contract freshness | PASS in Docker backend check command |
| Diff whitespace and unrelated-file exclusion | PASS |

The final committed-source Docker backend command exited **0**, including its
OpenAPI freshness check. This succeeded sequentially after the interrupted attempt.
The full 953-test run and final 806-test Docker run overlap; their counts must not
be added as distinct tests.

## Failures investigated, not hidden

- Initial regression tests failed for the old environment-selected migration target
  and absence of bounded lock waiting; they passed after implementation.
- Compose 2.24 rejected dependency-bearing `extends` and global overrides of imported
  services. The implementation uses `include` fragments and direct env-file fixture
  selection instead. Both minimum and current configuration checks pass.
- The full backend run initially found one old expectation that silently ignored a
  baseline target at a newer head. The test now explicitly asserts downgrade refusal,
  unchanged revision and successful head no-op. The next full run passed 953 tests.
- The external-volume addition initially left the default name empty. A new
  configuration assertion failed; the explicit project-scoped fallback fixes it,
  and the final runtime matrix validates preservation and missing-volume refusal.
- Test environment attempts encountered Windows temp permissions and missing Node /
  incompatible Windows dependency links in Linux. Repository-local host temp paths
  and a disposable complete Linux Node/Python test environment resolved these issues;
  assertions and interoperability cases were not removed.
- Docker Desktop interrupted concurrent image export/unpack and a later test attempt
  with RPC/EOF errors. Those attempts are inconclusive, not passes. Builds were
  retried sequentially; final labels/IDs and successful exit codes were checked.
- An unexpected Python exception could initially escape migration redaction. The
  new KeyError regression failed first; the guarded fallback now exits nonzero with
  only a safe code/type and execution identifier. No exception payload is printed.

## Operator handoff and limits

- Retain the existing project name. Standard volume identity remains
  `<project>_scope_creep_guard_postgres`. For an existing nonstandard volume, set
  both `SCOPE_GUARD_POSTGRES_VOLUME` and `SCOPE_GUARD_POSTGRES_VOLUME_EXTERNAL=true`;
  verify the resolved mount and backup first. No actual developer/production volume
  transition was performed; compatibility tests use representative owned fixtures.
- Existing-stack updates require maintenance downtime: prepare intended images,
  stop application services, force a fresh attached migration run, then recreate
  API/workers and finally frontend only after success. A failed migration leaves
  applications stopped. Correct the cause and rerun; incompatible rollback requires
  a verified backup. No zero-downtime claim is made.
- Older Drizzle / unbackfilled installations retain the explicit adoption and
  expansion/backfill/check procedure. This change does not automatically authorize
  adoption, bypass provenance or stamp unknown schemas.
- Dokploy configuration was validated locally, not deployed. Its operator must
  confirm Compose 2.24+ and configure the maintenance lifecycle instead of assuming
  ordinary redeploy stops old processes before DDL. No live provider call, customer
  data migration, production deployment or paid job was performed.
- The final report records local results. GitHub Actions execution is separate and
  must be inspected on the PR; remote CI success is not inferred from these runs.
