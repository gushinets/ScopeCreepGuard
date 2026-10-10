# Transitional ownership

Next.js under frontend owns UI/localization, page guards and the same-origin gateway. Four auth operations (register, login, logout, me) and five project operations (list/create/get/update/delete) forward to FastAPI once, preserving cookies and headers without retries or fallback. The remaining twelve operations, including legacy history creation, OpenAI integration, pending Drizzle owner lookup/database access, snapshots/proofs, evaluations, and browser PDF/extraction/currency helpers remain TypeScript-owned. Its migration target runs before its app container.

Python under backend owns startup/configuration/logging, GET /health/live and connectivity-only GET /health/ready, plus POST /api/auth/register, POST /api/auth/login, POST /api/auth/logout and GET /api/auth/me. Auth use cases orchestrate repositories and the inherited Unit of Work; infrastructure adapters implement bcrypt and the existing HS256 session format. Registration/login/me require configured database and shared AUTH_SECRET; logout/liveness do not. Production cookies require SCOPE_GUARD_PRODUCTION=true (the production image default). Public-page redirects confirm Python's owner lookup so deleted-user sessions can recover. Drizzle retains all migration authority. See any-639-data-model-and-contracts.md for schema and operational boundaries.

Python also owns GET/POST /api/projects and GET/PATCH/DELETE /api/projects/{id}. Routes handle transport and dependencies; project use cases orchestrate the inherited Unit of Work; repository ports separate workflows from SQLAlchemy adapters. Owned history reads include existing draft links. Project changes preserve saved snapshots; deletion uses existing database cascades. TS single-project helpers remain for pending workflows. No schema or migration ownership changes accompany this cutover.

Project cards use nested frozen value objects for agreed scope, dates, optional
client and pricing. Repository ports and application inputs/outputs carry these
values and tuples of immutable history entries. HTTP input/output conversion
stays in api/project_input.py and api/project_output.py; serializers allocate new
JSON structures and never expose internal state.

ANY-639 designs contracts/data and prepares SQLAlchemy/Alembic without transferring migration authority. ANY-640 migrates existing business/auth operations and routing deliberately. ANY-641 moves PDF/extraction/currency services. Root contracts are generated from implemented Python routes; frontend/lib/api is the shared browser/forwarding boundary.

Root tests/e2e covers complete user journeys; deploy/proxy records future routing. Frontend feature folders document future ownership without changing imports or presentation behavior. Historical documents under docs/superpowers and root product documents retain original paths as historical context; use README.md for current setup.
