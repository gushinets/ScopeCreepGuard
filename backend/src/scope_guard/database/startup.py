"""Container startup: explicit target, connectivity, then guarded Alembic."""

import argparse
import os
import sys
import time
from collections.abc import Callable

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from scope_guard.database.cli import main as migrate_main
from scope_guard.database.session import normalize_url


def target_url(environment: str) -> URL:
    value = os.environ.get(environment)
    if not value:
        raise ValueError("database_target_missing")
    url = normalize_url(value)
    if any(os.environ.get(key) for key in ("PGSERVICE", "PGSERVICEFILE", "PGHOSTADDR", "PGPORT")):
        raise ValueError("database_target_override_rejected")
    return url


def wait_for_database(
    url: URL,
    *,
    timeout: float = 120,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 3})
    deadline = clock() + timeout
    try:
        while True:
            try:
                with engine.connect() as connection:
                    connection.exec_driver_sql("SELECT 1")
                return
            except OperationalError as error:
                state = getattr(error.orig, "sqlstate", None)
                if state and not state.startswith("08") and state != "57P03":
                    raise ValueError("database_configuration_invalid") from None
                if clock() >= deadline:
                    raise RuntimeError("database_unavailable") from None
                sleep(min(1, max(0, deadline - clock())))
    finally:
        engine.dispose()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url-env", required=True)
    args = parser.parse_args(argv)
    try:
        wait_for_database(target_url(args.database_url_env))
        command = ["migrate", "--database-url-env", args.database_url_env]
        target = os.environ.get("SCOPE_GUARD_MIGRATION_TARGET")
        if target:
            command.extend(["--target", target])
        if os.environ.get("SCOPE_GUARD_ADOPT_LEGACY", "false") == "true":
            command.append("--adopt-legacy")
        return migrate_main(command)
    except (ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print("database_operation_failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
