SQLAlchemy models and Alembic metadata are the canonical schema source. Run the
guarded migration command from `backend/` with an explicitly named URL variable:

`python -m scope_guard.infrastructure.database.cli migrate --database-url-env SCOPE_GUARD_DATABASE_URL`

The command initializes empty databases, upgrades known Alembic revisions, and
validates the result. A compatible legacy Drizzle database additionally requires
`--adopt-legacy`; validation occurs before and after table locks and before the
baseline stamp commits. Unknown schemas, ledgers, or revisions fail without a
stamp. Repeated runs at head are safe. Application startup never runs migrations
or `create_all`, and destructive baseline downgrade is refused.
