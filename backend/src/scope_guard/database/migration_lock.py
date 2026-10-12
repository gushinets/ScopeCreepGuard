"""Serialize guarded migrations for all replicas of this database."""

from sqlalchemy.engine import Connection

MIGRATION_LOCK_ID = 642_000_001


def acquire_migration_lock(connection: Connection) -> None:
    # Unlike DDL locks, the replica coordination lock must wait for a migration
    # of any duration. The transaction owns it through validation and commit.
    connection.exec_driver_sql("SET LOCAL lock_timeout='0'")
    connection.exec_driver_sql("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK_ID,))
    connection.exec_driver_sql("SET LOCAL lock_timeout='10s'")
