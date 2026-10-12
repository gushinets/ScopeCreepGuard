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

- [ ] 1. Domain schemas/transitions/hashes and explicit ports; focused red/green tests.
- [ ] 2. Alembic expansion, guarded staging, resumable lossless backfill and validators.
- [ ] 3. Atomic project/Draft/revision/event persistence and ownership/concurrency tests.
- [ ] 4. Persisted analysis and protected generation/regeneration/translation workflows.
- [ ] 5. Explicit immutable History and analysis-derived evaluation feedback.
- [ ] 6. Finalization/void, private durable exports, storage adapter and worker.
- [ ] 7. Versioned API/gateway contracts and frontend autosave/user workflows.
- [ ] 8. Tighten/retire compatibility; full review, required checks and documentation.

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
