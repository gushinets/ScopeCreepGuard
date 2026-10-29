# ANY-758: shared Compose CI compatibility and integration PR validation

Date: 29 October 2026 (Europe/Moscow). Fix branch:
`codex/any-758-compose-ci-fix`. Base: freshly fetched
`origin/codex/any-758-email-verification-password-reset` at
`9da7aa54d5b4961d664b6c4ef591cee7cbe7f6d9`.

The original checkout was on `codex/any-779-async-smtp` with one untracked local
Mailpit diagnostic report. It was left untouched. This fix uses a separate managed
worktree and was not started from the SMTP feature branch. PR #46 was verified
Draft, with base main; PR #48 was verified open, with head
`codex/any-779-async-smtp-pr` and base the integration branch. Neither was changed.

## Reproduced cause

Both supplied CI logs contain the same Compose 2.24.0 failure:

- [PR #46 compose-minimum](https://github.com/gushinets/ScopeCreepGuard/actions/runs/40927877349/job/123638140378)
- [PR #48 compose-minimum](https://github.com/gushinets/ScopeCreepGuard/actions/runs/40946122528/job/123701814538)

The selected deployment file contains `include.env_file: compose/interpolation.env`
while its include project directory is the repository root. Compose 2.24.0's
loader passes that relative dotenv path to a reader that makes it absolute
against the process working directory. It searches `<repo>/compose/interpolation.env`
instead of `<repo>/deploy/compose/interpolation.env`.

This was reproduced on the untouched integration snapshot with the official
2.24.0 Windows binary and again with its official Linux binary. Both returned
exit 15 with the same missing-path error for the first full-stack config command.
No placeholder file, symlink, version bump, ignored failure or skipped job was used.

Source references:
[Compose 2.24.0 dependencies](https://github.com/docker/compose/blob/v2.24.0/go.mod),
[compose-go include loader](https://github.com/compose-spec/compose-go/blob/v2.0.0-beta.3/loader/include.go),
[dotenv path handling](https://github.com/compose-spec/compose-go/blob/v2.0.0-beta.3/dotenv/env.go),
[extends loader](https://github.com/compose-spec/compose-go/blob/v2.0.0-beta.3/loader/extends.go),
[official include documentation](https://docs.docker.com/reference/compose-file/include/).

A small synthetic path matrix also exposed a second compatibility difference:
relative `extends.file` inside an included role is resolved against the top-level
project by 2.24.0 and the included project by the current version. Fixing only the
first missing dotenv path would leave runtime inheritance broken.

## Correction and preserved behavior

All maintained root/deploy entry points now use include's standard optional dotenv
discovery, with no relative sentinel reference. The obsolete sentinel is removed.
The existing include `project_directory` keeps build contexts, container env-file
paths and mounts rooted at the repository. Service env-file chains are unchanged.

Backend, LLM worker and export worker now state the five inherited runtime
settings directly in their respective authoritative service environment maps.
Values are unchanged: database URL/default, production flag, log level and both
workflow flags. The unused cross-file runtime service is removed. There is still
only one definition of each service, shared by full and component entry points;
configuration checks assert consistency of common runtime values across roles.

The harness evaluates maintained files from a copied synthetic deployment fixture
instead of the developer checkout, preventing default include dotenv discovery
from reading real credentials or rescuing intentionally missing settings.
Only maintained Compose files, the non-secret bootstrap and small lifecycle helpers
are copied. A focused test proves user env files and unrelated reports are excluded.
Every configuration subprocess uses the requested Compose executable; previously,
explicit root/deploy parity calls still invoked the installed version directly.

Effective configuration comparison against the untouched integration snapshot on
Compose 5.6.0 found exact normalized equality for all 11 maintained entry points:
root, canonical full stack, two full-stack compatibility entries, six components,
and production/Dokploy. A separate synthetic external-volume case also matched.
Only checkout path prefixes were normalized; service environment, dependencies,
healthchecks, commands, build args, ports, networks and volume mappings were compared.

PostgreSQL volume identity/external mapping, explicit UUID test projects and the
migration completion gate are preserved. No schema/startup migration logic or
maintenance helper behavior changed. Mailpit's image/digest, internal SMTP,
loopback UI, retention, readiness, no-relay policy and scoped volume are unchanged.
Existing deploy/proxy and deploy/silo contents are preserved.

## Explicitly approved minimum-version startup exception

An additional minimal reproduction showed that Compose 2.24.0 does not reload a
parent `.env` after the non-secret deploy bootstrap sets `COMPOSE_FILE`. Current
Compose does. The user explicitly approved an env-file flag for deploy startup
on 2.24 rather than raising the minimum or copying secrets.

| Invocation with configured root .env | Compose 2.24.0 | Compose 5.6.0 |
| --- | --- | --- |
| Bare root `docker compose up -d --build` | Automatic root env supported | Automatic root env supported |
| Bare deploy `docker compose up -d --build` | Parent dotenv rediscovery unsupported; configuration regression records the expected failure | Automatic root env supported |
| Deploy `docker compose --env-file ../.env up -d --build` | Supported and checked for parity | Supported |
| Explicit root/deploy file selection with the same explicit synthetic env/project | Supported | Supported |

The bootstrap remains tracked and non-secret, containing only
`COMPOSE_FILE=../compose.yaml`; only its explanatory comment changes. Tests do
not silently accept an arbitrary minimum-version failure: they assert the known
discovery failure and require the explicit env-file fallback to match the root
configuration and its custom project/volume identity.

## Integration PR policy

The existing workflow now validates PRs into both main and the exact ANY-758
integration branch. Push coverage remains main and codex/**. No workflow or job
was duplicated, and compose-minimum remains required/running.

All jobs use the default PR merge checkout, preserving validation of the proposed
combined state. The rebase job separately evaluates the event's actual PR head SHA
against its actual fetched base. Base/head values enter through step environment
variables and quoted shell arguments, never executable expression interpolation.

Both configured base policies require the current base to be an ancestor of the
PR head. Integration task branches may merge integration updates. Main-targeted
PRs keep the existing no-merge-commits policy. Unsupported targets fail closed;
invalid/untrusted head values are passed to Git with end-of-options protection.
The synthetic checkout merge is not mistaken for a merge in the actual PR head.
The aggregate PR #46 stays Draft; any final linear-history preparation before
main remains separate. Workflow/check counts must not be described as test counts.

## Validation results

No application containers, databases or storage services were started for this
fix. This is configuration/policy verification, not a new full-stack runtime claim.
No fresh application images or revision labels are claimed. No database reset,
volume/image deletion, Docker prune or paid LLM call occurred.

| Check | Actual result |
| --- | --- |
| Official Compose 2.24.0 Windows and Linux checksums | Matched published release checksum files |
| Original integration config on 2.24.0, Windows and Linux | Reproduced missing sentinel error, exit 15 |
| Fixed configuration matrix on 2.24.0, Windows and Linux | Passed, including explicit legacy deploy env fallback |
| Fixed matrix on installed Windows Compose 5.6.0 and official Linux 5.6.0 | Passed, including bare root/deploy automatic env discovery |
| Root/canonical/compatibility/component/Dokploy parity | Passed for every maintained entry point |
| Custom project identity, scoped/external PostgreSQL mappings, migration gates | Passed |
| Mailpit loopback-only UI, internal SMTP, retention and no relay/auth relaxation | Passed configuration assertions |
| Before/after effective config comparison | All 11 entries identical; external-volume override identical |
| Git history/workflow/isolation regressions | 14 passed on Linux |
| Same tests plus existing maintenance helper regressions | 25 passed on Windows |
| Ruff check/format | Passed for changed Python code/tests |
| actionlint 1.7.7, bash syntax, ShellCheck | Passed on Linux |
| Independent read-only code review | No actionable findings |

The selected executable is used for every call in the configuration matrix,
including inside the bare-invocation fixture. Linux matrix runs had no Docker CLI
installed and no Docker socket mounted, so a hidden fallback to installed Compose
would have failed. Tools containers had bounded CPU/memory and were removed on
exit; tests used UUID-named temporary Git repositories/projects and synthetic values.

Verified binary SHA-256 values:

- Compose 2.24.0 linux-x86_64:
  `43fb39c0bc24ac796123935032eddcfb57a7acd9216badeb10714c986ea1e090`
- Compose 2.24.0 windows-x86_64.exe:
  `4e0e387d67a65d92e3a7aca085f86b4b46ed5bd7a475f81921629e1d097178f0`
- Compose 5.6.0 linux-x86_64:
  `40343e21ca777173e69cff5dbafeb37c6f81f3b0d57d9e597f036e95eb63e76a`
- actionlint 1.7.7 Linux archive:
  `023070a287cd8cccd71515fedc843f1985bf96c436b7effaecce67290e7e0757`

Local raw evidence is ignored under `output/compose-ci-fix/`: official checksum
files, `minimum-before-fix.txt`, `minimum-linux-before-fix.txt`, both Linux success
logs, `policy-linux-tests.txt`, `effective-config-parity.json`, actionlint/ShellCheck
logs and isolated probe fixtures. No real secrets or unrelated diagnostic reports
are included in this commit.

Reproducible commands, using separate downloaded binaries rather than replacing
the installed Compose:

```sh
uv run python backend/scripts/verify_docker_startup.py --config-only
uv run python backend/scripts/verify_docker_startup.py --config-only --compose-binary /PATH/TO/VERIFIED/compose-2.24.0
uv run python -m unittest discover -s ci/tests -v
uv run pytest ci/tests backend/tests/unit/test_stack_update.py -q
actionlint .github/workflows/ci.yml
bash -n ci/scripts/require-rebase.sh
shellcheck ci/scripts/require-rebase.sh
```

## Publication and subsequent PR #48 synchronization

Publish only the dedicated fix branch as a PR into
`codex/any-758-email-verification-password-reset`; do not merge it automatically.
No direct push to main/integration, force-push of the SMTP branch, Linear change,
PR #48 closure or conversion of PR #46 out of Draft is part of this fix.

After review and merge of the fix into integration, update PR #48 by merging its
updated integration base into its existing head, then push that normal merge:

```sh
git fetch origin
git switch codex/any-779-async-smtp-pr
git merge origin/codex/any-758-email-verification-password-reset
git push origin codex/any-779-async-smtp-pr
```

Do not cherry-pick a second copy of the fix into the SMTP branch. The resulting
push reruns both push and integration-targeted PR validation. Remote green checks
are not inferred from local results; observe the new runs after publication.
