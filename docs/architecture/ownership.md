# Transitional ownership

Next.js under frontend owns UI/localization, page guards and the same-origin gateway. All 21 current `/api/*` operations forward to FastAPI once, preserving cookies and headers without retries or fallback. Browser PDF/extraction/currency helpers remain unchanged. Drizzle's migration target runs before its app container.

Python under backend owns startup/configuration/logging, GET /health/live and connectivity-only GET /health/ready, plus POST /api/auth/register, POST /api/auth/login, POST /api/auth/logout and GET /api/auth/me. Auth use cases orchestrate repositories and the inherited Unit of Work; infrastructure adapters implement bcrypt and the existing HS256 session format. Registration/login/me require configured database and shared AUTH_SECRET; logout/liveness do not. Production cookies require SCOPE_GUARD_PRODUCTION=true (the production image default). Public-page redirects confirm Python's owner lookup so deleted-user sessions can recover. Drizzle retains all migration authority. See any-639-data-model-and-contracts.md for schema and operational boundaries.

Python also owns GET/POST /api/projects and GET/PATCH/DELETE /api/projects/{id}. Routes handle transport and dependencies; project use cases orchestrate the inherited Unit of Work; repository ports separate workflows from SQLAlchemy adapters. Owned history reads include existing draft links. Project changes preserve saved snapshots; deletion uses existing database cascades. TS single-project helpers remain for pending workflows. No schema or migration ownership changes accompany this cutover.

Project cards use nested frozen value objects for agreed scope, dates, optional
client and pricing. Repository ports and application inputs/outputs carry these
values and tuples of immutable history entries. HTTP input/output conversion
stays in api/project_input.py and api/project_output.py; serializers allocate new
JSON structures and never expose internal state.

ANY-639 designs contracts/data and prepares SQLAlchemy/Alembic without transferring migration authority. ANY-640 migrates existing business/auth operations and routing deliberately. ANY-641 moves PDF/extraction/currency services. Root contracts are generated from implemented Python routes; frontend/lib/api is the shared browser/forwarding boundary.

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
