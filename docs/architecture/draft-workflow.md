# Persistent Draft workflow — ANY-549

Current LLM publication and agreement rules: [17 October nonblocking workflow](2026-10-17-nonblocking-llm-workflow.md). This supersedes older coupled material readiness and full-context classification-staleness descriptions below.


PostgreSQL owns confirmed work and archives. `/api/v2` exposes versioned contracts;
localStorage is an explicit recovery buffer for unconfirmed edits only. See the
[approved implementation record](plans/2026-10-12-any-549-persistent-draft-workflow.md).

## Relationships and stored responsibilities

| Table | Responsibility and relationships |
| --- | --- |
| users | Existing identity; owns many projects. Authentication remains unchanged. |
| projects | Current scope, contacts, dates, exact decimal rates/prices; owner creation key/hash and updated/archive timestamps. Owns one working Draft and many analyses/archives. |
| drafts | Stable UUID, unique project, request text, analysis reference/staleness, version 2 JSON editor and positive BIGINT revision. |
| draft_revisions | Immutable full working-state/context snapshots; unique Draft/revision and Draft/operation, parameter hash, reason/actor/time. |
| analysis_runs | Frozen request/context/source revision/user/languages; immutable original result, status/model/prompt/error, key/hash and execution timestamps. Execution purpose lives in its immutable creation event. |
| history_entries | Immutable original completed-check snapshot plus explicit archives of edited materials, exact source DraftRevision, original analysis, saving user/key/hash/time. Existing UUIDs and evaluation links survive. |
| change_orders | Immutable finalized content/reference from History, optimistic finalized/voided state, revision/actor/timestamps/key/hash. |
| document_exports | Durable queue and private object metadata from finalized agreement; versions/language, lease/attempt/error, checksum/type/size, key/hash/timestamps. |
| activity_events | Immutable semantic references, revision/changed fields, actor, operation key and versioned limited payload. |
| evaluation_cases | Existing quality feedback/constraints plus original immutable analysis reference; inputs/results are derived on the server. |

Composite workflow/profile references bind links to the correct project and owner.
This is not a blanket LLM constraint: llm_operations owner/project/draft/run and
provider_calls operation/step use independent single-column FKs; their mutual
consistency also depends on service/repository checks (migration 0005). History references
`draft_revisions(draft_id, revision)`, never the changing current revision. Restrict
deletion protects retained records. Ordinary removal archives a project; no physical
deletion API or finite retention policy is enabled.

Reply tone/language and Change Order terms have one editable representation. AI
proposals are read-only provenance. Analysis results remain separate. Request or
relevant project changes invalidate the result. Save/revision/events commit together
with optimistic locking; completed retries precede stale-version rejection. Clear and
restore create new revisions of the same Draft. Restoration validates frozen context.

Model calls run outside transactions. Run completion and result application are
distinct; late results cannot overwrite changed Drafts. Model execution is not
exactly-once; result application is at most once. Regeneration uses persisted edited
reply; translation uses edited materials and frozen scope. Estimate refresh preserves
manual terms and the original analysis reference.

The completed check automatically publishes its original History snapshot against
a persisted revision. Explicit completion may additionally archive edited materials
for that same analysis; the original snapshot is never overwritten. Repeated commands
and identical snapshots are deduplicated. One analysis can therefore have multiple
History entries.
Viewing archives never changes Draft. Server references are globally unique; only
one active finalized agreement is permitted per archive. Void explicitly before
replacement. Finalization does not establish client acceptance or send anything.

## Maintenance rollout

These are operator instructions, not a rollout performed by this task. Back up and
stop legacy writes for the approved coordinated maintenance cutover. All operations
use `python -m scope_guard.database.cli` and an explicit database environment variable.

1. `migrate --database-url-env SCOPE_GUARD_DATABASE_URL --target 0002_workflow_expand`.
2. `workflow-backfill --database-url-env SCOPE_GUARD_DATABASE_URL`. Each project is
   locked/imported in its own transaction; reruns skip completed projects.
3. `workflow-check --database-url-env SCOPE_GUARD_DATABASE_URL`. Verify UUID sets,
   raw-envelope digests, relationships, evaluations and explicit missing provenance.
4. Advance `migrate` first to `0003_workflow_constraints`, then `0004_workflow_retire`.
   Only individually verified transferred rows are retired. The baseline is immutable.
5. Enable `SCOPE_GUARD_WORKFLOW_V2=true` in API/frontend together and set migration
   target `0004_workflow_retire`; deploy matching images.

Selection is `updated_at DESC, created_at DESC, UUID DESC`. The selected Draft keeps
its UUID; additional legacy Draft UUIDs become immutable import revision IDs. Import
order is not chronological edit history. Full raw states remain through read-only
legacy links. Missing historical scope/completion/results are never invented.
Unsupported editor conversion stops and rolls back that project for review instead
of silently altering old terms. Tighten/retire requires verified backfill. After v2
writes, use forward correction rather than destructive downgrade or old writers.

Default runtime remains at the original compatible baseline until operators enable
cutover. Legacy services fail closed on contracted schemas; v2 rejects unsafe old
API writes with upgrade-required. No user/production migration was run.

## Durable export runtime

`apps/worker/main.py` composes the backend worker, UoW, existing bounded PDF renderer
and private S3 adapter. It never migrates. `compose.workflow.yaml` is an explicit
rollout overlay. API and worker need the same explicit database URL.

Provision a private bucket. Configure `SCOPE_GUARD_EXPORT_BUCKET`, optional
`SCOPE_GUARD_EXPORT_ENDPOINT`, `SCOPE_GUARD_EXPORT_REGION`, access/secret keys or the
standard AWS credential chain. Grant put/get/list/delete for `exports/scg-`. Existing
model credentials remain required. No production infrastructure was provisioned.

PostgreSQL claims use `SKIP LOCKED`, 120-second persisted leases, 30-second renewal
and attempt fencing. Crashes are reclaimed; automatic retries stop after three
attempts, followed by explicit user retry. Each attempt uses a new conditional-write
object key. Ready files are never overwritten; downloads verify SHA-256. Orphans
older than 24 hours are removed while protecting live/ready attempts.

Retention defaults to indefinite. A separately selected worker setting
`SCOPE_GUARD_EXPORT_RETENTION_DAYS` expires ready files after removal while retaining
metadata/archives. A production retention change requires an explicit policy.
Filesystem storage and the source-built S3 server are isolated test implementations.

## Frontend and limits

Text debounce is 750ms with a five-second maximum interval. Structured edits save
immediately; actions flush pending writes. A tab serializes saves and queues edits;
old responses cannot replace newer text. Uncertain actions retain keys/parameters.
Conflicts preserve edits and require reviewing the server version before reapplying.
Recovery is explicit, validated and tagged with Draft/base revision. Reload/device
access restores confirmed server state; logout/navigation flush pending saves.

Generation admission still requires one production API worker/replica. Deployment,
real-data backfill, physical deletion, sending, acceptance and signatures remain
outside the authorized implementation.
