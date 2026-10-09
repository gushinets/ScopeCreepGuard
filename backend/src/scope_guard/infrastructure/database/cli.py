"""Explicit target selection; mutation is restricted to disposable verification in ANY-639."""

import argparse
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from scope_guard.infrastructure.database.migrations import adopt_baseline, upgrade_empty
from scope_guard.infrastructure.database.schema_verification import (
    SchemaCompatibilityError,
    verify_baseline,
)
from scope_guard.infrastructure.database.session import normalize_url


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("check", "upgrade-empty", "adopt-baseline"))
    parser.add_argument("--database-url-env", required=True)
    parser.add_argument("--disposable", action="store_true")
    args = parser.parse_args(argv)
    engine = None
    try:
        value = os.environ.get(args.database_url_env)
        if not value:
            raise ValueError("database_target_missing")
        url = normalize_url(value)
        if args.operation != "check" and (
            not args.disposable
            or args.database_url_env != "SCOPE_GUARD_TEST_DATABASE_URL"
            or url.username != "scg_test"
            or not url.database.startswith("scg_test_")
            or url.host not in {"127.0.0.1", "localhost"}
            or any(os.environ.get(key) for key in ("PGSERVICE", "PGSERVICEFILE", "PGHOSTADDR"))
        ):
            raise ValueError("disposable_target_required")
        engine = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 3})
        with engine.begin() as connection:
            connection.exec_driver_sql("SET LOCAL lock_timeout='3s'")
            {
                "check": verify_baseline,
                "upgrade-empty": upgrade_empty,
                "adopt-baseline": adopt_baseline,
            }[args.operation](connection)
        print("schema_compatible" if args.operation == "check" else "disposable_baseline_prepared")
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
