# ANY-549 — Persistent Draft Workflow Implementation Plan

Approved by the user on 2026-10-12. Execution: native in this chat.

## Goal and architecture

Implement the complete persistent Draft workflow specified in the conversation:
one working Draft per project, immutable analysis runs and revisions, explicit
History completion, finalized agreements and durable private PDF exports.
PostgreSQL is authoritative. API -> services -> domain/UoW -> repositories;
external generation, rendering and storage run outside database transactions.

## Base and checkout

Base: origin/main, 510e6cd1f1a7afb63202c1eab022447b2ffd9723.
Branch: codex/any-549-draft-workflow. Managed isolated worktree.
Original checkout: codex/ci-structure-and-compose-smoke, committed tree identical
to origin/main. Preserve its unstaged deletions of
idea-006-scope-creep-guard-2026-05-25.md,
interface-generation-prompt-template.md and scope-creep-guard-prd.md.
No push, PR, merge, deployment, publication or real-data migration is authorized.

## Binding decisions

- Preserve UUIDs, TIMESTAMPTZ, positive BIGINT revisions and Decimal money.
- One Draft UUID for the lifetime of each project; no workspace/final Draft state.
- Every working write has expectedRevision and operationId; completed retries
  precede version checks. Same key/different parameters is rejected.
- Draft, revision and semantic events commit atomically. Never trust submitted
  analyses, snapshots or ownership. Composite relationships prevent cross-project links.
- Analysis freezes persisted inputs/results and applies at most once only to an
  unchanged source revision. Model execution is not claimed exactly once.
- Versioned document stores reply and editable agreement fields, not original
  analysis, request or a complete project record. Preserve needed existing editor
  fields and generated alternatives, with one authoritative editable representation.
- History is a self-contained immutable completed-check snapshot, created only
  explicitly. It references draft_revisions, never the changing drafts.revision.
- Restore/clear create revisions. Restored analysis must match current context.
- Project removal archives; archived records and ready exports retained indefinitely.
- Extra legacy Draft IDs become immutable imported revision IDs. Select working
  state by updated_at DESC, created_at DESC, UUID DESC. Keep raw envelopes and
  missing provenance. Import ordering is never presented as edit chronology.
- Legacy History IDs/evaluation relationships retained. Mutable old editor content
  is migration capture, not proven original final content. No invented historical
  scope, result, revision or completion timestamp. Imported analysis is stale.
- Globally unique server-generated agreement references; one active agreement
  per HistoryEntry; explicit optimistic void before replacement. No client acceptance.
- S3-compatible private storage via Boto3; persistent test adapter. PostgreSQL
  export queue, restart-safe polling worker, fenced leases, immutable ready files,
  checksums, retries and orphan cleanup. No process-memory authoritative storage.
- Export lease 120s, heartbeat 30s, polling 2s; three automatic attempts, explicit
  retry afterward. Orphan grace 24h. No automatic expiry configured.
- New /api/v2 contracts; matched frontend/API cutover in maintenance window;
  obsolete unsafe writes return upgrade-required instead of bypassing concurrency.
- Autosave: 750ms debounce, 5s maximum, immediate structured edits, serialized
  saves and queued changes; saved/dirty/saving/failed/conflict. Flush dependent
  actions. Local recovery buffer never automatically overwrites server data.

## Ordered tasks

- [x] 1. Domain schemas/transitions/hashes and explicit ports; focused red/green tests.
- [x] 2. Alembic expansion, guarded staging, resumable lossless backfill and validators.
- [x] 3. Atomic project/Draft/revision/event persistence and ownership/concurrency tests.
- [x] 4. Persisted analysis and protected generation/regeneration/translation workflows.
- [x] 5. Explicit immutable History and analysis-derived evaluation feedback.
- [x] 6. Finalization/void, private durable exports, storage adapter and worker.
- [x] 7. Versioned API/gateway contracts and frontend autosave/user workflows.
- [x] 8. Tighten/retire compatibility; full review, required checks and documentation.

Each task: write meaningful tests first; observe expected failure; implement;
run relevant checks; inspect diff/staged files; explicitly stage task files;
create a coherent usable commit. Do not amend/rebase/force-push.

## Migration sequence

New guarded Alembic revisions only; immutable baseline/provenance fixtures stay.
Expand nullable fields/tables -> compatible reads/writes -> explicit resumable
per-project backfill -> compare UUID sets, counts, envelope hashes and relationships
-> switch authoritative reads -> tighten constraints -> retire obsolete paths/columns.
The runner supports explicit stages and refuses tighten/retire without verified
backfill. No large hidden startup backfill. Tests use owned disposable PostgreSQL.
Real-data execution requires a separately scheduled maintenance rollout.
Before cutover expanded legacy state supports rollback; after v2 writes, maintain
maintenance mode and forward-fix instead of destructive downgrade/old writers.

## Verification and review focus

Concurrent create/edit/retry; atomic rollback; stale/delayed model results; no
implicit History; exact immutable archive source; clear/restore/project/archive
preservation; cross-user and cross-project denial; agreement replacement/old
downloads; empty/legacy/interrupted/drift migrations; worker crash/upload/lease
fencing/orphans; frontend queued edits, failures, conflicting tabs and recovery.
Required gates: PostgreSQL integration-required pytest, architecture, Ruff,
Linux/Windows mypy, OpenAPI/generated types, frontend tests/lint/types/build,
gateway checks, PDF rendering verification and disposable Compose smoke.

## Initial evidence and external requirements

Inspection baseline: 385 passed, 4 failed, 6 setup errors. Targeted unsandboxed
run: 5 passed, 6 fixture errors; PDF/extraction API cases passed. Missing frontend
dependencies block auth interoperability; Windows temporary-directory permissions
block fixtures. Docker server 29.7.2 available. Establish configured baseline.
Production export requires private S3 endpoint/region/bucket/access, worker and
database configuration. Existing generation remains single-production-replica.

## Handoff and completion record

Update this record with actual commits, prepared/applied test migrations, check
results, external settings and limitations. Final report distinguishes original
checkout changes from implementation changes. No real database backfill is run.

### Completion — 2026-10-13

Implementation is complete on `codex/any-549-draft-workflow`, retained in the managed
worktree. No push, PR, merge or deployment was performed. Commits:

- `b484158`: approved plan, domain workflow rules and ports.
- `610c344`: persistence, staged Alembic migration, lossless import and exact validators.
- `16ae08d`: frozen analyses/generation, explicit History, evaluations, agreements,
  private durable exports, versioned API and integration verification.
- `78fcb03`: frontend restoration, autosave/queue/conflict/recovery, History and exports.
- The final verification/documentation commit follows these; its hash is in Git history.

Fresh verification evidence:

| Gate | Actual result |
| --- | --- |
| Backend `pytest --require-integration` | 464 passed; one existing Starlette/httpx deprecation warning. Includes disposable Compose startup/restart, migrations, authorization, PDF and real S3 restart checks. |
| Post-format migration/workflow suite | 7 passed after exact function manifest synchronization. |
| Simultaneous Draft writes and retry hash regression | 1 passed: one committed save, one 409, no duplicate revision, different retry parameters rejected. |
| Frontend Vitest | 43 files, 293 tests passed after all fixes. |
| Ruff check and format | Passed for backend, API and worker. |
| Linux and Windows mypy | Passed, 181 source files; existing untyped-function informational notes. |
| ESLint and TypeScript | Passed; one pre-existing unused `_s` test warning. |
| Next.js production build | Passed with persistent workflow enabled. |
| OpenAPI and generated frontend types | Both drift checks passed. |
| Workflow Compose configuration and worker image | Validated with synthetic values; worker image built locally. No deployment. |

The independent read-only review found three important defects. Each was reproduced
with a failing test and fixed: queued text behind an uncertain recovery save;
History disappearing from the project-edit response; and conflict reapplication
carrying stale generation provenance. All covering tests and final suites passed.
Additional regressions cover matching restored context, cross-export operation keys,
accepted recovery-buffer transfer and confirmed project writes followed by failed
reads. There are no deferred review findings.

Prepared migrations `0002_workflow_expand`, `0003_workflow_constraints` and
`0004_workflow_retire` were applied only to owned disposable empty/legacy test
databases. Existing baseline and legacy provenance fixtures are unchanged. UUIDs,
raw imported states, History/evaluation links and unknown historical provenance
were verified. No user/production database was migrated or backfilled.

See [entity structure, rollout and runtime instructions](../draft-workflow.md).
Operators own private bucket/credentials, worker deployment and a separately
scheduled real-data maintenance conversion. Retention remains indefinite; physical
deletion/retention changes require their own policy. Unsupported legacy editor
conversion fails for review rather than rewriting terms. Generation tests use a
deterministic provider; no billable live-model invocation was required. The existing
single production API worker/replica generation limitation remains.

### Execution rulings and costs

- Native Windows progress bookkeeping replaced POSIX skill scripts; no product
  behavior changed. Cost if wrong: bookkeeping repair only.
- Default startup stays at the immutable baseline until explicit matched cutover.
  Cost if activation is omitted: the new workflow remains disabled.
- Legacy retirement verifies each UUID/raw envelope/digest before retiring its
  transferred row. Cost if old data differs: conversion stops for review.
- Existing HTTP 400 validation behavior was retained. Cost if clients expect 422:
  they must follow the existing repository error contract.
- Unsupported editor conversion rolls back the project for review. Cost: manual
  resolution may be needed during real-data migration; original states are retained.
- The branch/worktree is kept, following the user's prohibition on unauthorized
  integration or publication. No further integration approval was requested.

The original checkout's three pre-existing document deletions remain unrelated
and untouched. Implementation changes are committed; ignored test artifacts are
excluded from commits. Final Git state is checked in the completion report.
