# Predictable Docker startup and migration lifecycle

Approved user plan, 24 October 2026. No issue identifier supplied.

## Checkout and ownership

Base: freshly fetched origin/main, `0bea6bc8c2e106f78dd2a14cbff4cb0b7e4c3d90`.
Branch: `codex/predictable-docker-startup`. Work in the existing checkout;
preserve untracked nine-issue acceptance documents and evidence. Implementation
and verification belong to this PR; operators own backups and deployment.
Do not merge or deploy. Architecture ownership remains in ../ownership.md.

## Design and scope

Replace workflow/LLM overlays with root and component Compose entry points using
authoritative service definitions and explicit dependency closures. Retain service
names and the `scope_creep_guard_postgres` volume key. Compose minimum: 2.24.
Root-level entry points keep path and default project resolution consistent.
Dokploy reuses definitions with deployment-only overrides and no local env files.

PostgreSQL healthy -> migrate successful -> backend / llm-worker / export-worker;
backend healthy -> app. Workers have no API dependency. API startup no longer
migrates; all processes retain schema checks. The release target comes from the
single packaged Alembic head (currently 0008_contextual_onboarding), never overlays.
Preserve unknown-revision, schema, explicit adoption and staged backfill safeguards.

Use the existing transaction advisory lock on the migration connection, with a
120-second configurable deadline. Recheck state after acquisition. Log correlation,
source, target, wait/acquisition/timeout, progress, no-op, completion, duration,
safe failure and exit outcome. Never print credentials or raw database exceptions.

Updates prepare images first, stop application services, ensure PostgreSQL health,
force-recreate and run migration attached, and recreate applications only on
success. Failure leaves applications stopped and volumes intact. This requires
maintenance downtime; no zero-downtime guarantee. No unrelated acceptance fixes.

## Ordered implementation

1. Add regression coverage for bounded locking, target selection, downgrade
   rejection, redaction, and topology; observe failures before implementing.
2. Implement guarded migration runner and locking/logging; separate API startup
   and validate worker schema readiness without submitting paid work.
3. Implement shared catalog, complete/component entry points, compatibility alias,
   Dokploy settings, update lifecycle and PowerShell convenience commands.
4. Update CI to test exact documented startup without target overrides; replace
   obsolete API-migration assumptions while retaining safety assertions.
5. Update AGENTS.md, README, environment examples and active references. Document
   commands, dependencies, precedence, existing-volume transition, failure recovery,
   image freshness, isolated tests and deployment requirements.
6. Run isolated Docker verification, review diff, record evidence and limitations,
   commit only scoped files, push, create and attach PR against main.

## Verification contract

Only disposable projects/databases/owned volumes; never reset existing databases.
Verify fresh full stack; 0007 upgrade with representative data; current no-op;
concurrent runners; failure gating; lock timeout; process-death release; each
component closure; component-to-full resource reuse; repeated successful/failed
updates; simulated existing volume; missing config; Dokploy config; existing
migration safety/provenance/schema/startup/signal/application/static/container checks.
Use existing disposable S3 fixture, synthetic credentials and no paid AI requests.
Test Compose 2.24 and installed 5.6 where available. Report failures and unexecuted
checks separately. Record tested revision, image identifiers and sanitized commands
in docs/architecture/2026-10-24-docker-startup-verification.md.

## Operator transition and handoff

Keep the existing Compose project name and resolved database volume. Check mounts
before startup; nonstandard volumes require an explicit external mapping. Preserve
legacy adoption authorization and lossless backfill procedure. Back up before
updates; rerun the maintenance lifecycle after correcting migration failures.
Do not claim plain Dokploy redeploy stops running old services safely.

## Execution record

Plan saved before implementation. Verification results and limitations will be
linked here before PR creation.

Ruling: Compose 2.24.0 reports false circular references and 2.24.7 rejects
`extends` of services declaring `depends_on`. Preserve the approved 2.24 minimum
by using `include` for canonical per-service fragments, keeping
compose.services.yaml as the catalog and `extends` only for environment settings.
Include models use an intentionally empty interpolation env file so an explicit
root --env-file cannot accidentally reload a developer .env in nested models.
This changes composition internals, not service identities or operator commands.

Ruling: Compose 2.24 cannot globally override imported services/volumes. Tests select
empty service env files through explicit path variables instead of adding an
isolation override. Nonstandard existing installations use an explicit volume name
and external=true; a missing named volume fails rather than creating an empty DB.
Preserve normal Compose project-name precedence in the wrapper by supplying -p only
when the operator explicitly selects --project. Production-only proxy forwarding
preserves local env-file precedence.

Implementation complete in f93fee5 with the explicit default-volume fallback fix in
2e6167d. Independent review found the wrapper project-name precedence and proxy
precedence issues; both were fixed and rechecked. Final source-labelled images and
complete runtime matrices pass Compose 5.6.0 and 2.24.0. Backend full run: 953 passes;
final Docker unit/API/architecture run: 806 passes; frontend: 383 passes. See
[verification and operator handoff](../2026-10-24-docker-startup-verification.md)
for exact source revision, image IDs, commands, failed attempts and limitations.
No paid AI jobs, changes to pre-existing developer/production databases, merge or
live deployment occurred.

## PR 42 review follow-up

Fix the confirmed partial-update cleanup and role-configuration findings without
changing the migration lifecycle or touching acceptance evidence. First reproduce
post-migration backend/worker/frontend startup failures and unrelated worker-setting
requirements. Stop all application services on maintenance failure after preparation,
preserve the original exit code if cleanup fails, and keep PostgreSQL/volumes intact.
Move auth, provider and storage requirements to their consuming service fragments.
Verify focused regression tests, minimal worker configurations on Compose 2.24 and
5.6, and disposable failed-startup scenarios, then update this PR without deploying.

Follow-up implemented in 4928b1a. Both findings reproduced, then 38 focused tests,
813 Docker unit/API/architecture tests and the expanded Compose 2.24 runtime matrix
passed. Tests cover failed backend/worker/frontend starts, original exit code after
cleanup failure, minimal role-only worker config and component logs. Fresh images
carry the follow-up revision. Independent review found no remaining actionable
issue; exact evidence and the initial unreproduced container-reuse failure are in
the verification report's PR 42 follow-up section. Acceptance evidence stays intact.
