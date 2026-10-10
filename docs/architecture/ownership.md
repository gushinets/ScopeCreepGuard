# Transitional ownership

Next.js under frontend owns UI/localization, page guards and the same-origin gateway. All 21 current `/api/*` operations forward to FastAPI once, preserving cookies and headers without retries or fallback. Browser PDF/extraction/currency helpers remain unchanged. The frontend has no PostgreSQL or migration responsibility.

Python under backend owns startup/configuration/logging, health endpoints, all public API operations, SQLAlchemy persistence, and Alembic migrations. Application startup never mutates schema. A backend-owned one-shot migration job validates and migrates PostgreSQL before FastAPI becomes ready. See any-639-data-model-and-contracts.md for schema invariants and the ANY-642 handover plan for operational boundaries.

Python also owns GET/POST /api/projects and GET/PATCH/DELETE /api/projects/{id}. Routes handle transport and dependencies; project use cases orchestrate the inherited Unit of Work; repository ports separate workflows from SQLAlchemy adapters. Owned history reads include existing draft links. Project changes preserve saved snapshots; deletion uses existing database cascades. TS single-project helpers remain for pending workflows. No schema or migration ownership changes accompany this cutover.

Project cards use nested frozen value objects for agreed scope, dates, optional
client and pricing. Repository ports and application inputs/outputs carry these
values and tuples of immutable history entries. HTTP input/output conversion
stays in api/project_input.py and api/project_output.py; serializers allocate new
JSON structures and never expose internal state.

ANY-639 designed contracts/data and prepared SQLAlchemy/Alembic. ANY-640 migrated existing business/auth operations and routing. ANY-642 transfers migration authority exclusively to Alembic. ANY-641 remains responsible for PDF/extraction/currency services. Root contracts are generated from implemented Python routes; frontend/lib/api is the shared browser/forwarding boundary.

Empty databases are created through Alembic. Legacy Drizzle databases require an
explicit adoption flag and must pass full catalog and historical-ledger validation
before the baseline can be stamped. Unknown or incompatible schemas are rejected
without mutation. The historical Drizzle ledger remains inert provenance.

Slice D transfers POST /api/analyze, /api/replies/regenerate,
/api/client-materials/language and /api/change-orders/estimate together. Routes
parse and map errors; analysis and change-order use cases orchestrate immutable
values and read-only repository ports. The inherited UoW rolls back/closes before
the OpenAI adapter runs. Generation never writes drafts, history or projects.
The Responses adapter owns the only retry layer, using the original model,
prompts, schemas, reasoning and per-attempt timeout. One app-scoped limiter admits
ten operations/user/rolling minute; production must use one worker and one replica.

Python issues and verifies the existing signed draft-proof format. TypeScript
proof verification and draft persistence validation now exist only in tests;
production TypeScript draft persistence is retired. Shared pure serialization allocates
fresh JSON for both infrastructure signing/prompt construction and the HTTP output
boundary. Provider schemas remain separate from permissive runtime normalization.
The frontend OpenAI SDK/key is retired; backend configuration owns the key and
outbound provider proxies. Deployment and rollback use a matching image pair,
with generation admission stopped/drained and a rolling-minute quiet window.

Root tests/e2e covers complete user journeys; deploy/proxy records future routing. Frontend feature folders document future ownership without changing imports or presentation behavior. Historical documents under docs/superpowers and root product documents retain original paths as historical context; use README.md for current setup.

Slice E transfers GET/POST /api/drafts and GET/PUT /api/drafts/{id}. Python
routes own ordered parsing, proof validation, error mapping and fresh JSON output.
Frozen/slotted nested draft values and recursively typed immutable JSON preserve
historical missing/null snapshots without normalizing reads. Repository ports
return detached domain values; SQLAlchemy adapters own joins, ownership predicates
and mutations; the inherited UoW owns commit/rollback/close. No schema change.

Creation validates the complete envelope/proof/document before write work, locks
the owned project then checks its creation key, atomically inserts one linked
history/draft pair and updates lastChecked. Valid retries return stored state
unchanged; expired proofs fail even for an existing key. PUT changes document,
client-material language, labels and updatedAt only. No draft operation calls LLM.
All draft GET responses, including errors and gateway outages, are private,no-store.
Deployment is a grouped four-operation cutover after backend availability and
draft-write draining; rollback uses the previous compatible image pair and keeps
persisted data. No request-level fallback or migration reversal.

Slice F transfers POST `/api/projects/{id}/history`, POST `/api/evaluations`,
GET `/api/evaluations/export` and POST `/api/locale`. Manual history uses the
project UoW to insert one entry and update `lastChecked` atomically, without a
draft, evaluation, snapshot change or provider call. Evaluation use cases resolve
the three accuracy labels from owned stored history; the SQLAlchemy adapter keeps
one evaluation per history entry and captures its required historical context.
Export is owner-filtered, ordered by creation time and ID, and serialized as the
legacy compact UTF-8 JSONL contract. Locale is public and writes only the existing
one-year cookie. Routes own parsing, response headers, cookies and error mapping;
repositories return frozen detached values. No table, migration or UI behavior
changes accompany this final API cutover.
