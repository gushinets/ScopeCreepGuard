# Durable document export worker

`main.py` composes the backend ExportWorker service, PostgreSQL queue/UoW, existing
PDF renderer and private S3 storage. The worker never runs Alembic migrations.

Use the export-worker Docker target or explicit compose.workflow.yaml overlay after
the coordinated ANY-549 maintenance migration. API and worker share a configured
database; configure a private bucket/credentials. Persisted leases/retries survive
restarts and ready exports remain downloadable. Retention defaults to indefinite.
No sending or outbox is introduced. Generation still requires one production API
worker/replica. See [runtime and rollout details](../../docs/architecture/draft-workflow.md).
