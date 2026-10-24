import argparse
import logging
import os
import sys
import time
from uuid import uuid4

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
        "operation",
        choices=(
            "check",
            "upgrade-empty",
            "adopt-baseline",
            "migrate",
            "workflow-backfill",
            "workflow-check",
        ),
    )
    parser.add_argument("--database-url-env", required=True)
    parser.add_argument("--disposable", action="store_true")
    parser.add_argument("--adopt-legacy", action="store_true")
    parser.add_argument("--target", default="0001_existing_drizzle_schema")
    args = parser.parse_args(argv)
    engine = None
    started = time.monotonic()
    logger = logging.getLogger("scope_guard.migration")
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s scope_guard.migration execution_id="
            + uuid4().hex
            + " %(message)s"
        )
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info("migration_execution_started operation=%s", args.operation)
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
        if args.operation == "workflow-backfill":
            from scope_guard.database.migrations import current_revision
            from scope_guard.database.workflow_backfill import backfill

            with engine.begin() as connection:
                if current_revision(connection) != "0002_workflow_expand":
                    raise ValueError("workflow_backfill_requires_expansion")
            print("workflow_projects_imported=" + str(backfill(engine)))
            return 0
        with engine.begin() as connection:
            connection.exec_driver_sql("SET LOCAL lock_timeout='3s'")
            if args.operation == "migrate":
                if args.target == "0001_existing_drizzle_schema":
                    migrate(connection, adopt_legacy=args.adopt_legacy)
                else:
                    migrate(connection, adopt_legacy=args.adopt_legacy, target=args.target)
            elif args.operation == "workflow-check":
                from scope_guard.database.workflow_backfill import verify_backfill

                verify_backfill(connection)
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
            "workflow-check": "workflow_backfill_verified",
        }
        print(messages[args.operation])
        logger.info(
            "migration_complete duration_seconds=%.3f exit_code=0", time.monotonic() - started
        )
        return 0
    except SchemaCompatibilityError as error:
        # Catalog object names and database exception text may contain private data.
        codes = sorted({item.path.split(".")[0] for item in error.differences})
        logger.error(
            "migration_failed code=schema_mismatch categories=%s exit_code=1", ",".join(codes)
        )
        print("schema_mismatch: " + ", ".join(codes), file=sys.stderr)
        return 1
    except ValueError as error:
        safe_codes = {
            "database_target_missing",
            "unsupported_database_url",
            "disposable_target_required",
            "database_target_override_rejected",
            "workflow_backfill_requires_expansion",
            "unknown_migration_target",
            "migration_downgrade_refused",
            "invalid_migration_lock_timeout",
        }
        code = str(error) if str(error) in safe_codes else "invalid_migration_configuration"
        logger.error("migration_failed code=%s exit_code=1", code)
        print(code, file=sys.stderr)
        return 1
    except (SQLAlchemyError, RuntimeError, TimeoutError) as error:
        code = (
            str(error)
            if str(error)
            in {
                "migration_lock_timeout",
                "migration_terminated",
                "workflow_backfill_incomplete",
                "legacy_envelope_integrity_failed",
            }
            else "database_operation_failed"
        )
        logger.error(
            "migration_failed code=%s error_type=%s exit_code=1", code, type(error).__name__
        )
        print(code, file=sys.stderr)
        return 1
    except Exception as error:
        # Unexpected migration/Alembic exceptions can embed private values in repr.
        logger.error(
            "migration_failed code=database_operation_failed error_type=%s exit_code=1",
            type(error).__name__,
        )
        print("database_operation_failed", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
        logger.info(
            "migration_execution_finished duration_seconds=%.3f", time.monotonic() - started
        )
        logger.removeHandler(handler)
        handler.close()


if __name__ == "__main__":
    raise SystemExit(main())
