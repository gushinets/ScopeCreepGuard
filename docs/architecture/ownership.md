# Transitional ownership

Next.js under frontend owns UI/localization, auth/page guards, every existing business API, OpenAI integration, Drizzle/database access, snapshots/proofs, evaluations, and browser PDF/extraction/currency helpers. Its migration target runs before its app container.

Python under backend owns only application startup, configuration, logging and GET /health/live. It needs no database, credentials or LLM provider. No SQLAlchemy/Alembic or readiness endpoint is introduced.

ANY-639 designs contracts/data and prepares SQLAlchemy/Alembic without transferring migration authority. ANY-640 migrates existing business/auth operations and routing deliberately. ANY-641 moves PDF/extraction/currency services. Root contracts are generated from implemented Python routes; frontend/lib/api remains the existing Next.js helper boundary until cutover.

Root tests/e2e covers complete user journeys; deploy/proxy records future routing. Frontend feature folders document future ownership without changing imports or presentation behavior. Historical documents under docs/superpowers and root product documents retain original paths as historical context; use README.md for current setup.
