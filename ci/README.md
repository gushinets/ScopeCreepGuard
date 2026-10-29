# CI structure

`.github/workflows/ci.yml` dispatches setup and verification from this directory.
The protected `rebase` job is retained. `actions/` pins Node/pnpm and Python/uv;
`contracts/openapi.json` records the API contract.

`check-containers.sh` validates full/component/Dokploy Compose contracts, builds
API, both worker roles and Nginx from the current revision, and checks retained
proxy/auth/upload/PDF behavior. `smoke-compose.sh` builds the fixed-source S3 test
fixture and runs `backend/scripts/verify_docker_startup.py` against those images.

The lifecycle harness selects `deploy/compose.yaml` and the documented
`deploy/compose.*.yaml` entry points explicitly. Configuration checks also verify
root/deploy bare-command parity and automatic root `.env` loading using a copied
fixture with synthetic values. The lifecycle harness selects empty test files through
`SCOPE_GUARD_LOCAL_ENV_FILE`, `SCOPE_GUARD_LOCAL_OVERRIDE_ENV_FILE` and
`SCOPE_GUARD_BACKEND_ENV_FILE` to avoid loading developer settings, supplies synthetic
settings, and uses UUID `scg-startup-test-*` projects. It never overrides migration
targets in release startup. Explicit historical targets are used only to prepare
previous-release fixtures. It verifies component closures, full readiness,
onboarding, locking/termination/failure gates, volume preservation and update
sequencing, plus Mailpit SMTP contents and persistence after restart.
Mailpit is verified by an isolated standard-library SMTP client, without public
application endpoints or external delivery. Disposable named volumes are retained;
removal requires explicit authorization. Container/network cleanup is restricted to the generated test project and labelled
storage fixture. No paid provider jobs are submitted.

Backend integration tests create their own PostgreSQL containers/databases.
`check-frontend.sh` runs the React suite, module boundaries, contract freshness,
types and build. The compatibility `verify_react_compose.py` delegates to the same
full lifecycle harness rather than constructing a modified service graph.

## ANY-758 integration PR validation

Push coverage remains `main` and `codex/**`. Pull-request coverage includes both
`main` and `codex/any-758-email-verification-password-reset`. Each validation job
uses the default proposed merge checkout. The `rebase` job keeps that checkout
but checks the event's actual head SHA against the fetched actual base branch;
branch values are passed through quoted environment variables, not shell source.
Both policies require the current base to be an ancestor of the PR head.
Integration-targeted task PRs may merge updates from the integration branch.
Main-targeted PRs still cannot introduce merge commits. The aggregate PR #46
stays Draft; preparing a final linear main-targeted history is a separate step.
A workflow/check count is not a test count.

The Compose matrix runs with the selected executable for every invocation,
including the root/deploy parity checks. All configurations are evaluated from
copied maintained definitions/helpers and synthetic env files; developer env
files and local diagnostic reports are excluded. Includes use standard optional
dotenv discovery rather than version-dependent relative sentinel paths. Roles
specify their effective runtime environment explicitly instead of cross-file
extends. Their shared database/workflow settings are checked for equality.

Minimum Compose 2.24.0 requires `--env-file ../.env` for startup from deploy;
current Compose discovers root `.env` through the bootstrap. The matrix verifies
the known 2.24 discovery limitation and the explicit fallback, not a silent skip.
Root bare startup, explicit root/deploy entries, all components, Dokploy, project
identity, volume mappings, migration gates and Mailpit boundaries are checked.
The existing minimum-version job still verifies the official binary checksum.
`ci/tests/` exercises branch histories and configuration-fixture isolation.

After this fix PR is reviewed and merged into the integration branch, synchronize
PR #48 by merging that updated base into its existing head branch:

```sh
git fetch origin
git switch codex/any-779-async-smtp-pr
git merge origin/codex/any-758-email-verification-password-reset
git push origin codex/any-779-async-smtp-pr
```

Do not cherry-pick the fix separately into the SMTP branch, force-push it, or
close PR #48. The push triggers fresh push and integration-targeted PR checks.
No fix is pushed directly to main or the integration branch.
