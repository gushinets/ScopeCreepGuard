import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import create_engine

from scope_guard.database.migrations import MIGRATION_LOCK_ID, current_revision, migrate
from scope_guard.database.session import normalize_url

pytestmark = pytest.mark.integration


def test_replica_waits_beyond_old_timeout_and_observes_committed_head(disposable_url):
    engine = create_engine(normalize_url(disposable_url))
    started = Event()

    def contender():
        with engine.begin() as connection:
            started.set()
            migrate(connection)
            return current_revision(connection)

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            with engine.begin() as first:
                first.exec_driver_sql("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK_ID,))
                future = pool.submit(contender)
                assert started.wait(5)
                time.sleep(11)
                assert not future.done(), "Replica must wait instead of failing at ten seconds"
                migrate(first)
            assert future.result(timeout=30) == "0001_existing_drizzle_schema"
    finally:
        engine.dispose()


def test_rollback_releases_transaction_lock(disposable_url):
    engine = create_engine(normalize_url(disposable_url))
    try:
        with engine.connect() as first, engine.connect() as second:
            first.exec_driver_sql("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK_ID,))
            assert (
                second.exec_driver_sql(
                    "SELECT pg_try_advisory_xact_lock(%s)", (MIGRATION_LOCK_ID,)
                ).scalar()
                is False
            )
            second.rollback()
            first.rollback()
            assert (
                second.exec_driver_sql(
                    "SELECT pg_try_advisory_xact_lock(%s)", (MIGRATION_LOCK_ID,)
                ).scalar()
                is True
            )
    finally:
        engine.dispose()


def test_process_death_releases_migration_lock(disposable_url, tmp_path):
    marker = tmp_path / "locked"
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("PG", "SCOPE_GUARD_"))
    }
    environment["SCOPE_GUARD_TEST_DATABASE_URL"] = disposable_url
    environment["SCG_LOCK_MARKER"] = str(marker)
    script = (
        "import os,time,psycopg; from pathlib import Path; "
        "connection=psycopg.connect(os.environ['SCOPE_GUARD_TEST_DATABASE_URL']); "
        f"connection.execute('SELECT pg_advisory_xact_lock({MIGRATION_LOCK_ID})'); "
        "Path(os.environ['SCG_LOCK_MARKER']).write_text('locked'); time.sleep(120)"
    )
    child = subprocess.Popen(
        [sys.executable, "-c", script],
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    engine = create_engine(normalize_url(disposable_url))
    try:
        deadline = time.monotonic() + 10
        while not marker.exists():
            assert child.poll() is None
            assert time.monotonic() < deadline
            time.sleep(0.1)
        with engine.begin() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT pg_try_advisory_xact_lock(%s)", (MIGRATION_LOCK_ID,)
                ).scalar()
                is False
            )
        child.kill()
        child.wait(timeout=10)
        with engine.begin() as connection:
            migrate(connection)
            assert current_revision(connection) == "0001_existing_drizzle_schema"
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=10)
        engine.dispose()
