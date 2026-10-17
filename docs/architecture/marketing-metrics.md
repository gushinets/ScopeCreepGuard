# Daily marketing metrics

`MetricsService(database.new_metrics_uow).read(start, end)` is the supported
programmatic access path. Both `read` and `reconcile` accept half-open UTC report
dates `[start, end)` and return ordered wide rows. An empty/reversed range raises
`ValueError`. Future report dates return no rows. Pre-0006 schemas return an empty
list explicitly; they are not treated as having measured zero usage.

Each call conservatively repairs every report day from the oldest source or
existing metric through the current UTC day. Requested earlier empty days are
also materialized. This repairs late completions, changed current feedback,
exclusion flags, and idle expiry of calendar windows without a new business
event. Direct table reads bypass repair and must inspect freshness themselves.
No global metrics HTTP route, dashboard, export, scheduler, or new worker exists.

## Transactions and recovery

`SqlAlchemyUnitOfWork.commit()` explicitly performs this sequence for a dirty
business/accounting UoW:

1. Commit T1 and mark it finished.
2. Close its session, releasing its database connection.
3. Invoke and synchronously await the application-level reconciliation callback
   supplied by `Database.new_uow()`.
4. The callback opens an independent T2 UoW/session through `new_metrics_uow()`.
5. Log reconciliation exceptions without undoing T1 or reporting the completed
   business action as failed.

This is an explicit application callback, not a SQLAlchemy transaction event
hook. T2's own UoW has no callback, preventing recursive reconciliation.
Confirmed activity marks the transaction dirty. Provider reservations/physical
call admission, completed accounting, and accepted/rejected validation also
mark their independent commits dirty, including late usage after terminal
operation status. Session touches alone do not trigger metrics.

T2 acquires one global transaction advisory lock before a single READ COMMITTED source
projection statement. All projected source facts share that statement snapshot.
`data_through` is its post-lock `statement_timestamp()`; `calculated_at` is a
later database `clock_timestamp()`. Complete rows are atomically upserted, with
an additional monotonic `data_through` condition. The lock avoids old snapshots
overwriting later calculations. Source IDs are never used as commit checkpoints.

T2 exceptions are logged and cannot roll back or turn the committed action into
a failed action. The next dirty action or explicit metrics read retries from
committed sources, including after process interruption. Without any action or
read there is no freshness guarantee. Cancellation can interrupt reconciliation;
the same persisted-source repair path applies on the next access.

For synchronous regeneration/translation, the failure handler checks the persisted
draft operation receipt before recording failure. Cancellation after T1 retains
the committed success without appending a contradictory failure event. Cancellation
still propagates to that caller; retrying the same command key recovers its saved
result without another generation call.

## Definition version 1

- All populations exclude `profiles.analytics_excluded`. Professional status
  `inactive` does not exclude a profile. Ownership uses the existing one-profile
  per-user relation, including projects in the nullable ownership transition.
- A successful baseline check is one successful analysis run with explicit
  saved History, counted at the earliest actual saved completion. Multiple
  archives of that run count once. Estimate purpose and linked estimate
  operations exclude those runs. Unverified legacy History never invents a
  successful timestamp. New logical runs remain separate even with equal text.
- Meaningful activity is a saved baseline check or finalized change order.
  Voiding a change order keeps the earlier finalization fact and adds the void
  count on its own day. DAU and MAU are distinct profiles; MAU covers the report
  day and previous 29 calendar days. Feature adoption intersects successful
  same-day users with DAU. PQL requires three distinct checks and a finalized
  change order in that same 30-day window.
- Registration and cumulative activation/TTV populations use the earlier of
  report day end and source cutoff. Activation requires a first saved check
  within `[registration, registration + 7 days)`; only fully elapsed seven-day
  registrations enter its denominator and numerator. A later first check still
  contributes TTV. D7/D30 return uses the exact target calendar day of a timely
  activation cohort. Current incomplete-day retention and empty rates are NULL.
- Durable operations are counted once; synchronous runs and generation events
  are included only when no durable operation owns them. Historical successful
  regeneration/translation revisions remain observable successes with unknown
  start/duration. Admission timestamps assign starts, terminal timestamps assign
  outcomes and durations; queue/retry time is included. Succeeded / (succeeded +
  failed + cancelled) excludes pending and PDF. Median/P95 interpolate original
  duration observations, never daily aggregates. Sample sizes remain explicit.
- Feedback is the current owner's evaluation once per saved baseline run, on
  that run's saved completion day. Reconciliation replaces a former evaluation;
  it does not reconstruct the feedback distribution as it was on a past date.
- AI physical calls and eventual usage/cost/validation belong to `started_at`
  UTC date. Retry means semantic attempt >1 OR transport attempt >1, once per
  call. Stage numbering and first reviewer calls do not imply retry. Each token
  total is NULL if any included call lacks that token observation.
  `ai_usage_unknown_calls` counts missing input OR output usage; optional cached/
  reasoning omissions have a distinct quality note. Estimated cost sums only
  stored `estimated_cost`, retaining its existing configured pricing policy;
  missing estimates make the sum NULL. Reservations and assessed/reported cost
  do not substitute for estimated cost. Validation percentages use known
  accepted/rejected results only, with NULL for an empty denominator.

## Quality and limits

Typed quality-note codes distinguish unverified legacy history, unknown operation
start, incomplete input/output usage, incomplete optional usage, incomplete
estimated cost, and the current unfinished report day. `is_partial` is true when
any note applies. This design does not infer missing historical sessions, hidden
operations, acceptance/payment, or successful saved checks from estimates.

The existing deletion behavior and restrictive source relationships remain.
Analytics can only reconcile retained source facts; it cannot restore deleted
facts or historical exclusion/feedback values that were not retained. Server-owned
source maintenance must mark its UoW dirty or invoke the supported read/reconcile
path after committing. No new deletion/anonymization policy is introduced.

Every reconciliation reloads retained source facts and recalculates every report
day from the oldest source/existing row (or an earlier requested date) through
today. This also occurs after dirty business and provider-accounting commits,
including late usage/validation updates. A separate transaction does not imply
background execution: these callers synchronously await T2, so its lock wait,
source loading, calculation and persistence contribute to completion latency.
The one global lock serializes all reconciliations, rather than just writes for
one date. Runtime, memory and upsert cost grow with retained facts and report
days. This full-history strategy deliberately favors recovery correctness and
remains unchanged. Idle stored rows can become stale; supported `read`/`reconcile`
must repair relevant windows before use. No incremental checkpoint, cache or
background worker is provided. Any later optimization must preserve post-lock
snapshot ordering, late-fact repair, explicit freshness and source completeness.

## Product-session collection

The signed HttpOnly `scg_browser` cookie supplies an opaque browser identity;
authentication continues to resolve the actor independently. Successful auth
hydration installs a missing browser cookie before the interaction observer is
enabled. The UI serializes that handshake across tabs with Web Locks. A browser
without Web Locks retains single-tab behavior, but simultaneous first hydration
in multiple tabs can split its initial session; that compatibility fallback does
not provide the shared-tab guarantee.

Only trusted, visible pointer, keyboard, input and wheel interactions send the
explicit session observation. Background polling, autosave, provider completion,
read requests and duplicate command receipts do not extend inactivity. Provider
completion events retain the initiating session even after its inactivity limit;
they do not create a replacement session. Observations establish neither product
success nor authorization. Session-only observations do not recalculate metrics,
because no session-duration KPI was agreed.

Each mounted observer sends the first eligible interaction promptly, then allows
at most one attempt per 30 seconds and one in-flight request. Continued genuine
input can send again after both constraints clear. Failed attempts consume the
same window. There is no timer, trailing observation, queued input or automatic
retry. Cleanup aborts pending delivery and disposes the old observer on logout,
user change or unmount; a same-user object refresh retains its window. Remounts
create a fresh observer; this is an observer-local bound, not a cross-tab rate
limit. Browser identity and the shared server session remain unchanged.

Coalescing approximates the last interaction time: with prompt successful
delivery and no blocking request, the last submitted observation can precede the
final genuine interaction by less than 30 seconds. Server receipt timestamps
remain authoritative. Slow/in-flight/failed delivery, network delay and teardown
can add uncertainty beyond that bound; aborting delivery cannot undo a request
already accepted by the server. No trailing request repairs idle time. The
30-minute inactivity rule still uses retained server observations and confirmed
business activity; authentication expiry and DAU/MAU definitions are unchanged.
