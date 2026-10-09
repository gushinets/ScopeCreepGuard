# Transitional ownership

Next.js under frontend owns UI/localization, auth/page guards, every existing business API, OpenAI integration, Drizzle/database access, snapshots/proofs, evaluations, and browser PDF/extraction/currency helpers. Its migration target runs before its app container.

Python under backend owns startup/configuration/logging, GET /health/live and connectivity-only GET /health/ready. ANY-639 prepares SQLAlchemy mappings, Pydantic contracts, explicit Unit of Work and guarded Alembic baseline verification without receiving business traffic or migration authority. Database configuration is optional for startup/liveness. See any-639-data-model-and-contracts.md for schema and operational boundaries.

ANY-639 designs contracts/data and prepares SQLAlchemy/Alembic without transferring migration authority. ANY-640 migrates existing business/auth operations and routing deliberately. ANY-641 moves PDF/extraction/currency services. Root contracts are generated from implemented Python routes; frontend/lib/api remains the existing Next.js helper boundary until cutover.

Root tests/e2e covers complete user journeys; deploy/proxy records future routing. Frontend feature folders document future ownership without changing imports or presentation behavior. Historical documents under docs/superpowers and root product documents retain original paths as historical context; use README.md for current setup.
