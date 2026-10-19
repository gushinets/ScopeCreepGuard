# Durable workers

`main.py` composes the backend ExportWorker service, PostgreSQL queue/UoW, existing
PDF renderer and private S3 storage. The worker never runs Alembic migrations.

Use the export-worker Docker target or explicit compose.workflow.yaml overlay after
the coordinated ANY-549 maintenance migration. API and worker share a configured
database; configure a private bucket/credentials. Persisted leases/retries survive
restarts and ready exports remain downloadable. Retention defaults to indefinite.
No sending or outbox is introduced. Generation still requires one production API
worker/replica. See [runtime and rollout details](../../docs/architecture/draft-workflow.md).

ANY-663 adds `SCOPE_GUARD_WORKER_ROLE=llm` to this same entrypoint/image. This role
composes ProviderGateway, LiteLLM Responses and PydanticAI, and claims operations
from PostgreSQL independently of HTTP requests. It requires the workflow flags,
shared database, provider key/model and a usable price bound; it does not require
export storage. The default role remains export.

For the standalone React frontend, complete the guarded migration/backfill and
verification through compatible `0007_nonblocking_llm` before coordinated
API/frontend/worker activation. The React application uses the persistent workflow.
The LLM role checks schema on startup without migrating. Its persisted leases,
fencing, accepted stages and provider-call reservations permit bounded recovery;
SIGTERM stops claims, drains for 30 seconds and then cancels local work. Use the
`compose.llm.yaml` overlay with `compose.workflow.yaml`; the container grace period
is 40 seconds. See [configuration, evidence and limitations](../../docs/architecture/any-663-verification.md).

For separate development, run `uv run python ../apps/worker/main.py` from
`backend/` in two terminals: set `SCOPE_GUARD_WORKER_ROLE=llm` in one and
`SCOPE_GUARD_WORKER_ROLE=export` in the other. Both use the same explicitly configured
development database as the API. Configure provider/model/rate bounds for the LLM
role and private export storage for the export role. Starting these workers does
not migrate the database.
