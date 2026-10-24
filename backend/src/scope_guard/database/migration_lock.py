"""Serialize guarded migrations for all replicas of this database."""

import logging
import math
import os
import time

from sqlalchemy.engine import Connection

MIGRATION_LOCK_ID = 642_000_001


def acquire_migration_lock(connection: Connection, *, timeout: float | None = None) -> None:
    """The caller's transaction owns the lock through schema verification and commit."""
    if timeout is None:
        timeout = float(os.environ.get("SCOPE_GUARD_MIGRATION_LOCK_TIMEOUT_SECONDS", "120"))
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("invalid_migration_lock_timeout")
    logger = logging.getLogger("scope_guard.migration")
    deadline = time.monotonic() + timeout
    waiting = False
    while True:
        if connection.exec_driver_sql(
            "SELECT pg_try_advisory_xact_lock(%s)", (MIGRATION_LOCK_ID,)
        ).scalar():
            logger.info("migration_lock_acquired")
            return
        if not waiting:
            logger.info("migration_lock_waiting timeout_seconds=%s", timeout)
            waiting = True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            logger.error("migration_lock_timeout")
            raise TimeoutError("migration_lock_timeout")
        time.sleep(min(0.25, remaining))
