# Application ownership

`frontend` owns UI/localization, browser/editor state, page guards and the
same-origin gateway. It forwards all 24 public API operations once, preserving
headers/cookies/cancellation without retries or fallback. It has no database,
provider-key or migration responsibility.

`apps/api` is the deployable FastAPI composition root: routes, request/response
schemas, transport parsing, dependency injection, authentication extraction,
error mapping, OpenAPI and bootstrap. Routes call backend services; concrete
adapter construction is confined to bootstrap. Health routes use a service.

`backend/domain` owns immutable business values, validation, classification,
draft/Change Order/project rules and explicit repository contracts. It imports
no API, ORM, migrations or integrations. Pure BCP47 and JavaScript compatibility
utilities preserve existing language/number/date/null behavior.

`backend/services` owns use cases and transactions, using domain types and
stable ports. Every write commits explicitly through a UoW; failures roll back.
Read-only work closes before provider calls. Lists/history/export use named query
ports and existing detached ProjectDetail, DraftSummary and EvaluationExport
read DTOs; no ORM objects cross this boundary.

`backend/database` owns SQLAlchemy mappings, repositories, optimized read SQL,
sessions/UoWs and guarded Alembic support. All table names, enum values, precision,
foreign keys, indexes, cascades and migration provenance remain unchanged.

`backend/integrations` owns OpenAI/prompts, auth adapters, PDF/localization/fonts,
scope readers and bounded isolated child processes. Services depend on ports.
Isolated processes import backend validation, never API. Limits, Unicode fonts,
sanitized environments, cancellation and temporary cleanup remain intact.

The API container is the migration composition root. PostgreSQL health precedes
entrypoint startup; entrypoint waits for connectivity and runs the guarded runner
under transaction advisory lock 642000001. Replicas wait, then revalidate committed
state. Commit/rollback releases the lock. Only successful migration starts API;
API readiness gates frontend. Import/OpenAPI generation never migrates. No
separate migrate service or required Compose profile remains.

Draft creation retains proof expiry/binding and atomic history/draft/lastChecked
updates under the owned-project lock and creation key. Saved snapshots stay
immutable; legacy absent/null context remains readable. Evaluation upsert and
owner-filtered JSONL preserve existing semantics. PDFs use saved/editor values,
never rerun analysis or recalculate original money. Scope extraction remains
temporary and editable; no currency conversion or rate provider is introduced.

Runtime dependencies: frontend -> API -> services/domain; bootstrap -> concrete
database/integration adapters; adapters -> service ports/domain; database ->
PostgreSQL. Backend never imports API/frontend. The root uv lock pins both Python
distributions; API owns FastAPI/Uvicorn/multipart dependencies.

`apps/worker/README.md` records future service-only/outbox possibilities. There is
no worker container, queue or jobs table. Generation admission remains local to
one production API worker/replica. Migration locking alone does not enable
multi-replica production generation. Deploy/rollback matching application image
pairs without destructive migration reversal. Historical migration verification
documents remain historical evidence; the application-boundaries record captures
current verification.
