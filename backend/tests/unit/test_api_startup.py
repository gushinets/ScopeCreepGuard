import importlib.util

import pytest


def test_container_startup_has_guarded_backend_runner():
    assert importlib.util.find_spec("scope_guard.database.startup"), (
        "Missing guarded startup runner"
    )


def test_startup_rejects_missing_target_before_waiting(monkeypatch, capsys):
    from scope_guard.database.startup import main

    monkeypatch.delenv("SCOPE_GUARD_DATABASE_URL", raising=False)
    assert main(["--database-url-env", "SCOPE_GUARD_DATABASE_URL"]) == 1
    assert "database_target_missing" in capsys.readouterr().err


@pytest.mark.parametrize("override", ["PGPORT", "PGSERVICE", "PGSERVICEFILE", "PGHOSTADDR"])
def test_startup_rejects_target_overrides_before_connecting(monkeypatch, capsys, override):
    from scope_guard.database.startup import main

    monkeypatch.setenv("SCOPE_GUARD_DATABASE_URL", "postgresql://user:x@localhost/test")
    monkeypatch.setenv(override, "invalid")
    assert main(["--database-url-env", "SCOPE_GUARD_DATABASE_URL"]) == 1
    assert "database_target_override_rejected" in capsys.readouterr().err


def test_startup_waits_then_passes_explicit_adoption(monkeypatch):
    from scope_guard.database import startup

    calls = []
    monkeypatch.setenv("SCOPE_GUARD_DATABASE_URL", "postgresql://user:x@localhost/test")
    monkeypatch.setenv("SCOPE_GUARD_ADOPT_LEGACY", "true")
    monkeypatch.setattr(startup, "wait_for_database", lambda value: calls.append("ready"))
    monkeypatch.setattr(startup, "migrate_main", lambda args: calls.append(args) or 0)
    assert startup.main(["--database-url-env", "SCOPE_GUARD_DATABASE_URL"]) == 0
    assert calls == [
        "ready",
        [
            "migrate",
            "--database-url-env",
            "SCOPE_GUARD_DATABASE_URL",
            "--target",
            "head",
            "--adopt-legacy",
        ],
    ]


def test_failed_migration_is_returned_to_entrypoint(monkeypatch):
    from scope_guard.database import startup

    monkeypatch.setenv("SCOPE_GUARD_DATABASE_URL", "postgresql://user:x@localhost/test")
    monkeypatch.setattr(startup, "wait_for_database", lambda value: None)
    monkeypatch.setattr(startup, "migrate_main", lambda args: 1)
    assert startup.main(["--database-url-env", "SCOPE_GUARD_DATABASE_URL"]) == 1


def test_transient_connectivity_is_retried_and_engine_closed(monkeypatch):
    from sqlalchemy.exc import OperationalError

    from scope_guard.database import startup

    attempts, sleeps, closed = [], [], []

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def exec_driver_sql(self, query):
            assert query == "SELECT 1"

    class Engine:
        def connect(self):
            attempts.append(1)
            if len(attempts) == 1:
                raise OperationalError(None, None, RuntimeError("connection refused"))
            return Connection()

        def dispose(self):
            closed.append(True)

    monkeypatch.setattr(startup, "create_engine", lambda *args, **kwargs: Engine())
    startup.wait_for_database(
        startup.normalize_url("postgresql://user:x@localhost/test"),
        clock=lambda: 0,
        sleep=sleeps.append,
    )
    assert len(attempts) == 2 and sleeps == [1] and closed == [True]


def test_nonconnectivity_failure_is_not_retried(monkeypatch):
    from sqlalchemy.exc import OperationalError

    from scope_guard.database import startup

    class InvalidDatabase(Exception):
        sqlstate = "3D000"

    class Engine:
        def connect(self):
            raise OperationalError(None, None, InvalidDatabase())

        def dispose(self):
            pass

    monkeypatch.setattr(startup, "create_engine", lambda *args, **kwargs: Engine())
    with pytest.raises(ValueError, match="database_configuration_invalid"):
        startup.wait_for_database(
            startup.normalize_url("postgresql://user:x@localhost/test"),
            sleep=lambda _: pytest.fail("Invalid configuration must not retry"),
        )


def test_app_and_openapi_do_not_run_startup_migrations(monkeypatch):
    from scope_guard_api.main import create_app

    from scope_guard.core.config import Settings
    from scope_guard.database import migrations, startup

    def forbidden(*args, **kwargs):
        pytest.fail("Application construction/OpenAPI must not migrate")

    monkeypatch.setattr(migrations, "migrate", forbidden)
    monkeypatch.setattr(startup, "main", forbidden)
    assert "/api/projects" in create_app(Settings(_env_file=None)).openapi()["paths"]
