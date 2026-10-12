import argparse
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from scope_guard.database.migrations import adopt_baseline, migrate, upgrade_empty
from scope_guard.database.schema_verification import (
    SchemaCompatibilityError,
    verify_baseline,
)
from scope_guard.database.session import normalize_url

"""Explicit target selection for guarded Alembic migration operations."""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation", choices=("check", "upgrade-empty", "adopt-baseline", "migrate")
    )
    parser.add_argument("--database-url-env", required=True)
    parser.add_argument("--disposable", action="store_true")
    parser.add_argument("--adopt-legacy", action="store_true")
    args = parser.parse_args(argv)
    engine = None
    try:
        value = os.environ.get(args.database_url_env)
        if not value:
            raise ValueError("database_target_missing")
        url = normalize_url(value)
        if args.operation in {"upgrade-empty", "adopt-baseline"} and (
            not args.disposable
            or args.database_url_env != "SCOPE_GUARD_TEST_DATABASE_URL"
            or url.username != "scg_test"
            or not (url.database or "").startswith("scg_test_")
            or url.host not in {"127.0.0.1", "localhost"}
            or any(
                os.environ.get(key)
                for key in ("PGSERVICE", "PGSERVICEFILE", "PGHOSTADDR", "PGPORT")
            )
        ):
            raise ValueError("disposable_target_required")
        if args.operation == "migrate" and any(
            os.environ.get(key) for key in ("PGSERVICE", "PGSERVICEFILE", "PGHOSTADDR", "PGPORT")
        ):
            raise ValueError("database_target_override_rejected")
        engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 3})
        with engine.begin() as connection:
            connection.exec_driver_sql("SET LOCAL lock_timeout='3s'")
            if args.operation == "migrate":
                migrate(connection, adopt_legacy=args.adopt_legacy)
            else:
                {
                    "check": verify_baseline,
                    "upgrade-empty": upgrade_empty,
                    "adopt-baseline": adopt_baseline,
                }[args.operation](connection)
        messages = {
            "check": "schema_compatible",
            "migrate": "migration_complete",
            "upgrade-empty": "disposable_baseline_prepared",
            "adopt-baseline": "disposable_baseline_prepared",
        }
        print(messages[args.operation])
        return 0
    except SchemaCompatibilityError as error:
        print(str(error), file=sys.stderr)
        return 1
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (SQLAlchemyError, RuntimeError):
        print("database_operation_failed", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
