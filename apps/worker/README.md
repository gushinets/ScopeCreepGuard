# Durable workers

`main.py` composes the LLM or PDF export worker. Both verify schema compatibility
before polling; neither runs Alembic. Compose migration success is their startup
gate, with no dependency on the API. The worker healthcheck requires a live polling
loop and a recent database-backed readiness heartbeat.

Use `compose.llm-worker.yaml` or `compose.export-worker.yaml` with the same explicit
project name as `compose.yaml`. See the root README for direct commands, shared
configuration and the maintenance update procedure. Full application verification
requires both workers, API, frontend, PostgreSQL and test object storage.

The LLM role (`SCOPE_GUARD_WORKER_ROLE=llm`) uses workflow flags, shared database,
provider key/model and conservative token-price bounds. Starting it does not submit
a provider job. SIGTERM stops claims, drains for 30 seconds and cancels local work;
Compose grants 40 seconds. The default role is `exports`, requiring private storage.
Persisted leases/retries survive restarts. Ready exports remain downloadable;
retention defaults to indefinite. No sending/outbox is introduced.

For native development, run `uv run python ../apps/worker/main.py` from `backend/`
with roles `llm` and `exports` in separate terminals, after the explicit migration
stage. Existing legacy databases must first complete the guarded adoption and
expansion/backfill/check procedure in
[the rollout guide](../../docs/architecture/draft-workflow.md).
