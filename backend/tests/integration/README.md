Integration tests own disposable PostgreSQL servers and databases; never use an
application URL or volume. Run `uv run --no-sync pytest --require-integration`
from backend after synchronizing all root workspace packages/groups.

The Compose startup test renders tracked topology without environment resolution,
substitutes synthetic configuration, creates a uniquely named stack/volume, tests
authentication, gateway reads/writes, restart, replica startup and migration failure,
then verifies ownership labels before cleanup. Signal tests use labeled disposable
containers with a controlled migration child. Existing migration revisions and
frozen Drizzle provenance fixtures must remain unchanged.

API liveness tests under tests/api require no external integrations. Domain/service
architecture checks include lazy and transitive imports; services depend on ports
and detached DTOs. Every write failure must leave no partial persisted records.
