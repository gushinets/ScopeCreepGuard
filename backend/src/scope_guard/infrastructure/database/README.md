SQLAlchemy models and Alembic metadata are the canonical schema source. Run the
guarded migration command from `backend/` with an explicitly named URL variable:

`python -m scope_guard.infrastructure.database.cli migrate --database-url-env SCOPE_GUARD_DATABASE_URL`

The command initializes empty databases, discovers known Alembic revisions from
the local script lineage, upgrades them to the configured head, and validates
the result. The immutable baseline catalog check applies to
`0001_existing_drizzle_schema`; descendant revisions use the managed-schema
validator so intentional later schema changes are not rejected. Add a
revision-specific validator when a future revision needs checks beyond the
shared application boundary.

A compatible legacy Drizzle database has no `alembic_version` table and
additionally requires `--adopt-legacy`; ledger and immutable baseline validation
occur before and after table locks and before the baseline stamp commits. Unknown
schemas, ledgers, malformed/multiple/foreign/unknown Alembic revisions fail
without a stamp. Repeated runs at head are safe. Application startup never runs
migrations or `create_all`, and destructive baseline downgrade is refused.
