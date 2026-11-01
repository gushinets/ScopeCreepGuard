# Durable workers

`main.py` composes the LLM or PDF export worker. Both verify schema compatibility
before polling; neither runs Alembic. Compose migration success is their startup
gate, with no dependency on the API. The worker healthcheck requires a live polling
loop and a recent database-backed readiness heartbeat.

Use `deploy/compose.llm-worker.yaml` or `deploy/compose.export-worker.yaml` with the same explicit
project name as `deploy/compose.yaml`. See the root README for direct commands, shared
configuration and the maintenance update procedure. Full application verification
requires both workers, API, frontend, PostgreSQL, Mailpit and private test object storage.

The LLM role (`SCOPE_GUARD_WORKER_ROLE=llm`) uses workflow flags, shared database,
provider key/model and conservative token-price bounds. Starting it does not submit
a provider job. SIGTERM stops claims, drains for 30 seconds and cancels local work;
Compose grants 40 seconds. The default role is `exports`, requiring private storage.
Persisted leases/retries survive restarts. Ready exports remain downloadable;
retention defaults to indefinite. No sending/outbox is introduced.

## Optional diagnostic semantic review

Optional internal semantic review of generated output, disabled by default.
Set `SCOPE_GUARD_LLM_SEMANTIC_REVIEW_ENABLED=true` in the root `.env` to opt newly
created diagnostic jobs into review. Missing/false keeps the llm-worker running
primary generation and local observations, with zero new diagnostic provider calls.
Only replies, reply, change_order and estimate outputs are supported; analysis
remains local. Review observes frozen generated output, never current user edits,
and cannot reject, repair or republish a completed primary result.

The job freezes opt-in and reviewer versions. Missing historical opt-in stays
disabled; enabling never backfills results. Runtime false also blocks new dispatch
for an opted-in job, including transport retries. Received candidates and accepted
decisions can be recovered without a call. Unknown dispatched outcomes are not
submitted again. Expired jobs keep their historical failure/deadline.

Review uses the existing diagnostic model and only the parent's remaining call/cost
budget, with one review per supported stage and at most two transport attempts.
Internal JSON outcomes distinguish clean, findings, disabled, insufficient budget,
incompatible version and failure; skipped/failed does not mean passed. Source
operation/step, output hash, source/reviewer versions and existing provider-call
relationships retain model, usage and cost attribution.

Changing `.env` is not hot reload: recreate `llm-worker` using the documented
maintenance sequence and the existing project name. Build the new binary first,
stop/drain all old worker processes for that deployment, run the one-shot migration
gate, then recreate the worker (initially with false). A new flag cannot control an
old binary. Already submitted provider requests may finish and incur accounted cost.

For native development, run `uv run python ../apps/worker/main.py` from `backend/`
with roles `llm` and `exports` in separate terminals, after the explicit migration
stage. Existing legacy databases must first complete the guarded adoption and
expansion/backfill/check procedure in
[the rollout guide](../../docs/architecture/draft-workflow.md).
