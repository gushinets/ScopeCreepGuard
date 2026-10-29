# ANY-778: deployment relocation and local Mailpit

Current status: the local image corruption has been repaired. Full-stack readiness
and SMTP acceptance/content/restart checks now pass. Earlier failure records below
are preserved as historical diagnostic evidence; see the final repair section.

Date: 29 October 2026 (Europe/Moscow). Branch:
`codex/any-758-email-verification-password-reset`.
Tested HEAD: `120917720f606705b46d38c124b99b86c350b544`.
Initial tracked/untracked Git status was clean. Tests used the uncommitted
deployment changes described below; the revision label alone does not identify
those local changes. No commit, push, PR, Linear comment or status change was made.

## Result and limitations

Configuration verification passed for every maintained entry point, including
root/deploy normalized equality with the same explicit synthetic environment and
project name. Maintenance helper tests: **11 passed**. Ruff checks passed.

**Full application readiness and SMTP reception are not verified.** The official
Mailpit v1.32.0 Linux amd64 executable exits with signal 11 / code 139 before
logging, including when invoked solely with `--version`. The platform-specific
manifest reproduces the failure. This is an observed runtime blocker on this
Docker host; its underlying cause has not been established. No image substitution,
schema workaround, authentication relaxation or host security relaxation was used.

In a real canonical full-stack attempt, PostgreSQL, backend, frontend and both
workers became healthy, and the one-shot migrator exited 0 at
`0008_contextual_onboarding`. Both workers logged `worker_ready schema_verified=true`.
Mailpit remained restarting/unhealthy. The full-stack `up --wait` exited 1; a
subsequent bounded wait for the other application services exited 0. Mailpit
therefore did not gate their startup. Its DNS name resolved from backend, but
SMTP connectivity did not succeed. Message acceptance, API text/HTML contents and
restart persistence remain unverified. The reusable SMTP verifier is implemented
but has not completed successfully against this selected image on this host.

No remote Dokploy deployment was performed. Minimum Compose 2.24 compatibility
remains covered by the existing CI job; it was not separately executed locally.
Local Docker Engine: 29.8.2; Docker Desktop: 4.95.0; Compose: 5.6.0;
platform: Linux amd64 on WSL2.

## Changes

- Moved all root `compose*.yaml` and `docker-compose*.yml` entry points into the
  existing `deploy/`, including compatibility entry points and Dokploy.
- Moved shared definitions and interpolation sentinel from `docker/compose/` to
  `deploy/compose/`. Existing `deploy/silo/init.sh` is unchanged; routing
  documentation in `deploy/proxy/README.md` now describes the migration gate.
- Canonical `deploy/compose.yaml` includes authoritative definitions directly.
  Compatibility files repeat only the include list, not service definitions;
  configuration tests assert exact parity. Direct includes avoid a nested include
  environment/path resolution failure observed in local Compose.
- Includes retain the repository root as project directory for build contexts,
  service env files and mounts. Shared runtime extends paths were updated.
  Dokploy's concrete frontend build context now points to `../frontend`.
- Default project identity remains `scopecreepguard`; `-p` and
  `COMPOSE_PROJECT_NAME` retain precedence. PostgreSQL volume key/name and its
  optional external-volume mapping remain unchanged. No global Mailpit volume
  name is introduced. Neither migration code nor migration dependencies changed.
- Updated the existing Python/PowerShell startup helpers, README, worker/CI/proxy
  documentation, AGENTS.md and `.env.example`. Helpers load the root `.env`
  explicitly by default. Historical reports/plans were left unchanged.
- Added Mailpit and an isolated standard-library SMTP verification client. It
  checks sender, recipient, subject, text and HTML through the Mailpit API,
  restarts the service and checks the same message ID and contents again.
  CI's existing lifecycle harness invokes it after full-stack startup.
- Test harness cleanup now retains named volumes rather than removing them.
  No application authentication, email dispatch, outbox, email worker or schema
  changes were implemented.

## Commands and identity

From the repository root, after configuring the root `.env`:

```powershell
docker compose --env-file .env -f deploy/compose.yaml up -d --build
```

From `deploy/`:

```powershell
docker compose --env-file ../.env up -d --build
```

Explicit environment-file arguments are required for consistent interpolation
across the two working directories. The environment is not implicitly copied
into `deploy/`. Preserve an existing installation's actual project name with
`-p EXISTING_PROJECT` or `COMPOSE_PROJECT_NAME`; inspect its PostgreSQL mount
before applying a relocation. A new project name selects new volumes.

Mailpit alone, from root:

```powershell
docker compose -f deploy/compose.mailpit.yaml up -d
python scripts/verify_mailpit.py
```

The verification command creates its own UUID project and retains its disposable
volume after stopping its containers. `--project` selects an already running
isolated test stack; `--client-image` can use its freshly built API image as the
Python client. It never adds an application endpoint.

Maintenance remains `python scripts/stack.py update --project EXISTING_PROJECT
--env-file DEPLOY_ENV` (add `--production` for Dokploy): prepare images, stop app
roles, wait for PostgreSQL, run the forced one-shot migrator, and start roles only
after success. Production also retains Silo initialization before migration.
Legacy adoption/backfill safeguards and failure cleanup remain intact. To update
local Mailpit independently, use its documented component entry point with the
same project name; it is not part of the application migration gate.

Dokploy operator action: change Compose Path from `docker-compose.dokploy.yml`
to `deploy/docker-compose.dokploy.yml`, retaining Git source contents, project
identity, variables, volumes and the documented maintenance procedure. Production
does not include local Mailpit or a public Mailpit proxy route.

## Mailpit boundaries

- Internal SMTP: `mailpit:1025`; no host SMTP binding, credentials or TLS.
- UI: `127.0.0.1:${MAILPIT_UI_PORT:-8025}:8025`, normally
  <http://localhost:8025>; tests use port `0`.
- SQLite: `/data/mailpit.db` in `<project>_scope_creep_guard_mailpit`.
  Retention: at most 500 messages and 7 days; restart policy `unless-stopped`.
- Image-supported `/mailpit readyz` health check. No backend/worker dependency
  on Mailpit, relay/forwarding settings or permissive SMTP authentication flags.
- Actual container HostConfig confirmed only the loopback UI binding; no SMTP
  binding. Runtime application checks failed as described above.
- `no-reply-scopecreepguard@mail.com` is strictly a local test sender. No external
  inbox delivery was attempted or verified.

## Image and security evidence

Selected official image:
`axllent/mailpit:v1.32.0@sha256:0790692be935ea4420d085694f7985b1f692ca6a8771ab0e0bd8ba75ac180498`.
Registry resolution used `docker buildx imagetools inspect axllent/mailpit:v1.32.0`.
Linux amd64 manifest:
`sha256:938ce54b7b946ef3f45a03e119952cf7e67a7969d61f45a3ed055442a77e00f4`.

Upstream advisory review on this date:

| Advisory | Affected | Fixed | Selected version |
| --- | --- | --- | --- |
| [GHSA-379p-g4f4-hq5h](https://github.com/axllent/mailpit/security/advisories/GHSA-379p-g4f4-hq5h), High | through 1.31.6 | 1.32.0 | outside affected range |
| [GHSA-2vgv-6hcp-mf43](https://github.com/axllent/mailpit/security/advisories/GHSA-2vgv-6hcp-mf43), Moderate | 1.30.4–1.31.1 | 1.31.2 | outside affected range |
| [GHSA-r553-m4fv-5v97](https://github.com/advisories/GHSA-r553-m4fv-5v97), Moderate | 1.30.0–before 1.30.5 | 1.30.5 | outside affected range |

The [advisory index](https://github.com/axllent/mailpit/security/advisories) and
[v1.32.0 release](https://github.com/axllent/mailpit/releases/tag/v1.32.0) were
rechecked. v1.32.0 was the latest stable release shown. No newer supported release
fixing the dependency findings below was established, so the requested version
was retained with unresolved findings explicitly recorded.

Docker Scout v1.26.0 could not scan because it required Docker login. Trivy
v0.69.3 successfully scanned the registry digest on Linux amd64, with a freshly
downloaded vulnerability database and no severity/package suppression. Scanner
container digest: `sha256:bcc376de8d77cfe086a917230e818dc9f8528e3c852f7b1aff648949b6258d1c`.
The initial unbounded attempt lost the Docker connection during DB download;
the successful invocation used `--memory 1g` and `--parallel 1`.

```text
trivy image --parallel 1 --platform linux/amd64 --scanners vuln --quiet --format json \
  axllent/mailpit:v1.32.0@sha256:0790692be935ea4420d085694f7985b1f692ca6a8771ab0e0bd8ba75ac180498
```

Final scan timestamp: `2026-10-29T15:37:31.281330527Z`.
Database schema version: 2; updated `2026-10-29T13:09:46.269823229Z`,
downloaded `2026-10-29T15:37:26.867298283Z`, next update `2026-10-30T13:09:46.269822928Z`.
The metadata was captured from the same container as this final scan:
[database metadata](mailpit-scan-db-2026-10-29.json).

Raw findings: [scan JSON](mailpit-scan-2026-10-29.json). All three findings are
Go module findings in `/mailpit`; Trivy reported zero Alpine 3.24.3 OS package
findings and did not report a Mailpit application advisory. That is a scanner
result, not a claim that the image has no vulnerabilities.

| Finding | Scanner severity | Package / installed | Fixed version | Deployment relevance |
| --- | --- | --- | --- | --- |
| GO-2026-5932 | UNKNOWN | `golang.org/x/crypto` v0.58.0 | none listed | Advisory concerns the unmaintained OpenPGP packages. This deployment does not configure OpenPGP, but binary call reachability has not been proven; finding retained. |
| CVE-2026-78661 | UNKNOWN | `golang.org/x/net` v0.61.0 | v0.62.0 | HTML parsing can allocate quadratically on crafted text; relevant to processing untrusted captured email. Reachability/exploitability was not dynamically assessed. |
| CVE-2026-97045 | UNKNOWN | `golang.org/x/net` v0.61.0 | v0.62.0 | HTML rendering namespace handling; potentially relevant to captured email HTML. Reachability/exploitability was not dynamically assessed. |

Trivy supplied no CVSS/vendor severity for these records; UNKNOWN is preserved,
not converted to Low. See the [Go OpenPGP advisory](https://pkg.go.dev/vuln/GO-2026-5932)
and [Go HTML rendering advisory](https://pkg.go.dev/vuln/GO-2026-6866).
No findings were dismissed on the grounds that Mailpit is local.

## Runtime evidence and test isolation

Final isolated project and statuses: [runtime JSON](any-778-runtime-2026-10-29.json).
All credentials were synthetic, all published test ports were dynamic, and the
private object-storage fixture had no published ports. No paid LLM jobs were
submitted. The documented source-built MinIO fixture build lost its Docker
connection; the bounded full-stack run instead used the repository's existing
pinned Silo image as external private test storage. Its test bucket was created
and explicitly set private with `mcli`. No service/dependency override was used.

Fresh application builds used `SOURCE_REVISION` equal to the HEAD above:

| Image | Fresh image ID | Revision label |
| --- | --- | --- |
| `scope-guard-api:any778` | `sha256:23125fb76569f9588e8235fa18b24533bed7aaec43548944ea1a49275db0a3aa` | tested HEAD |
| `scope-guard-worker:any778` | `sha256:5b7a529c2bfd940499a95bdd7f86b3c4336dc9f4d3cb37584b60d0c112922ec1` | tested HEAD |
| `scope-guard-frontend:any778` | `sha256:53b661f72ee7e231ee843bc9c29fed74d741c7d6b479fb7df2c15c5f6c746a49` | tested HEAD |

Configuration command: `uv run --with pyyaml --with httpx python
backend/scripts/verify_docker_startup.py --config-only`.
Helper tests: `uv run --with pytest python -m pytest
backend/tests/unit/test_stack_update.py -q`.
Builds used the existing API Dockerfile (runner/export-worker targets) and
frontend runner target; no application source changes were needed.

Disposable containers/networks were stopped/removed using their exact project
identity. Named volumes were retained, including failed Mailpit-only diagnostic
projects. No existing database was reset, no volume was removed and no prune was
run. Detailed synthetic local command logs are retained under ignored
`output/any778/`; they are not part of the maintained deployment source.

## Files and final Git state

Deployment entry points: `deploy/compose.yaml`, `deploy/compose.postgres.yaml`,
`deploy/compose.backend.yaml`, `deploy/compose.frontend.yaml`,
`deploy/compose.llm-worker.yaml`, `deploy/compose.export-worker.yaml`,
`deploy/compose.mailpit.yaml`, `deploy/compose.services.yaml`,
`deploy/docker-compose.yml`, `deploy/docker-compose.dokploy.yml`.
Their original root paths are deleted as part of the relocation.

All 16 original `docker/compose/` definition/sentinel files moved to
`deploy/compose/`; backend and worker runtime extends references changed paths.
`deploy/compose/mailpit.yaml` is new. No pre-existing Silo initialization content
was replaced. The only pre-existing file changed inside deploy is proxy documentation.

Other changed files: `.env.example`, `AGENTS.md`, `README.md`,
`apps/worker/README.md`, `ci/README.md`, `ci/scripts/smoke-compose.sh`,
`scripts/stack.py`, `scripts/dev.ps1`, `backend/scripts/verify_docker_startup.py`.
New maintained verification helper: `scripts/verify_mailpit.py`.
Evidence: this report, `any-778-runtime-2026-10-29.json`,
`mailpit-scan-2026-10-29.json`, `mailpit-scan-db-2026-10-29.json`.

Final state: same requested branch/HEAD, uncommitted tracked edits/deletions and
untracked relocated/new files; nothing staged or committed. Local scratch logs
under ignored `output/any778/` remain local. Historical reports and plans were
not rewritten. No WORKLOG or private agent file is included in the change set.

## Follow-up: bare root startup

At the user's subsequent request, root `compose.yaml` is now a thin include of
canonical `deploy/compose.yaml`, with `project_directory: deploy` and the existing
empty interpolation sentinel. It contains no service definitions. This is an
explicit convenience exception to the earlier relocation-only root layout.

The supported root startup command is now:

```powershell
docker compose up -d --build
```

Root `.env` is loaded automatically, including `COMPOSE_PROJECT_NAME`. The existing
service env-file chain `.env`, `.env.local`, `backend/.env` remains unchanged.
The deploy-directory command retains `--env-file ../.env` when selecting that
same root environment. No symlinks, copies of user secrets, or launcher changes
are needed.

Configuration verification was rerun: root convenience/canonical parity and all
entry points passed. A copied deployment fixture with only synthetic root `.env`
values proved automatic loading, custom project-name/volume preservation and
normalized equality with the explicit canonical command. No existing deployment
was started and no runtime readiness claim is added; the Mailpit exit-139 blocker
recorded above remains unresolved. The changes since the earlier image builds
are the root include, configuration checks and associated documentation.

## Follow-up correction: bare startup from deploy

The previous bare-command follow-up covered only repository-root invocation.
It did not satisfy the user's intended working directory, `deploy/`.

Both directories now support `docker compose up -d --build` without flags.
Tracked `deploy/.env` contains only `COMPOSE_FILE=../compose.yaml`; Compose loads
that bootstrap, selects the root project, then loads root `.env` automatically.
The Git ignore exception applies only to this non-secret bootstrap. User secrets
remain in the ignored root/role environment files; none were copied or changed.

Root `compose.yaml` now directly includes the shared service files instead of
nesting the canonical deploy entry point. Nested includes failed path rebasing
when selected by a relative COMPOSE_FILE, so both entry points list the same
shared files with their respective path bases. No service definition is copied.
Normalized parity checks cover both entry points, aliases and component files.

A copied fixture using synthetic secrets and a custom COMPOSE_PROJECT_NAME passed
bare `docker compose config` from both root and deploy, with exact normalized
configuration equality, correct root env values and unchanged project-scoped
volume names. This supersedes the earlier requirement for `--env-file ../.env`
for bare deploy startup. Explicit `-f` component commands may still select an env
file explicitly. The known Mailpit runtime failure remains a separate limitation.

## Diagnostic follow-up: local Mailpit binary truncation confirmed

The exit-139 root cause is now narrowed to a truncated binary in the local
Docker image filesystem, rather than the registry's published amd64 binary.
Local `/mailpit`: 20,971,520 bytes, SHA-256
`07a1f3ea1f90cf815ddbada3ac88fa06114506a10b72498be5c8dd1196e07fee`.
Its ELF load segments end at offsets 24,514,200 and 25,915,136, past local EOF.

Downloaded registry layer
`sha256:6d36f2406fac87880e6a1fc468122946d4cd699ae6f84c5d26e1c000441ae1ea`
was verified against its SHA-256. Its `/mailpit` is 25,915,552 bytes, SHA-256
`50326f3b223adcbd5071c33d93c04ba47b3295287eb2c735aff7076c06a212f4`,
with all ELF load segments within file bounds. Binding this verified binary
read-only over `/mailpit` in the exact same pinned image successfully executed
`mailpit version`: v1.32.0, go1.27.3, linux/amd64. This diagnostic did not change
Compose configuration, deploy a custom binary, remove images or touch volumes.
The 386 variant also executes; an async-preemption diagnostic did not repair
the truncated amd64 file. (`version` is the correct CLI subcommand; `--version`
is not supported, although the truncated binary crashes before parsing it.)

The local Docker content/snapshot extraction or storage needs repair/recreation
for this image. What originally truncated the local file is not established;
previous Docker EOF/resource failures are context, not proof of a specific cause.
Full SMTP verification remains pending until the unmodified image filesystem is
restored. Diagnostic files remain in ignored `output/any778/mailpit-diagnosis/`.

## Repair completed and verification repeated

Only the two unused local Mailpit image references were removed (the pinned
multi-platform index and amd64 manifest). No dependent containers existed, no
force removal was used, and no volumes, databases or unrelated images were
removed. The same official pinned v1.32.0 index was pulled again for linux/amd64.
The restored `/mailpit` is 25,915,552 bytes, SHA-256
`50326f3b223adcbd5071c33d93c04ba47b3295287eb2c735aff7076c06a212f4`,
matching the verified registry file. `mailpit version` now executes successfully
without a bind-mounted binary or any Compose/image/security workaround.

`python scripts/verify_mailpit.py --client-image scope-guard-api:any778` passed:
real SMTP acceptance, sender/recipient/subject/text/HTML via the API, unchanged
message after restart, loopback-only UI, no host SMTP binding and no relay.

Canonical full-stack verification was repeated with UUID project
`scg-any778-bc7622e8f3cc4da8a56c0604939b68b0`, a new project-scoped PostgreSQL volume and
private pinned Silo test storage. Full `up --wait` exited 0; all six persistent
services were healthy and `migrate` exited 0. SMTP checks inside this stack also
exited 0. Backend DNS/SMTP connectivity succeeded. No paid jobs were submitted.
Application images and revision labels remain those recorded above; since their
build, source changes affected only Compose entry points, configuration tests and
documentation. No application code changed.

Updated successful evidence: [repaired runtime JSON](any-778-runtime-repaired-2026-10-29.json).
Earlier failed runtime evidence is retained separately. Test containers/networks
were removed by exact test identity, and their named volumes were retained.
Root/deploy configuration parity and automatic .env checks were rerun and passed.
The registry image/digest and dependency scan findings did not change; the three
Go module findings remain unresolved. No remote deployment was performed.
