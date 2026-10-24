import logging

import pytest


def test_lock_wait_is_bounded_and_observable(monkeypatch, caplog):
    from scope_guard.database import migration_lock

    elapsed = [0.0]

    class Result:
        def scalar(self):
            return False

    class Connection:
        def exec_driver_sql(self, query, parameters=None):
            assert "pg_try_advisory_xact_lock" in query
            return Result()

    monkeypatch.setattr(migration_lock.time, "monotonic", lambda: elapsed[0])
    monkeypatch.setattr(
        migration_lock.time, "sleep", lambda seconds: elapsed.__setitem__(0, elapsed[0] + seconds)
    )
    with caplog.at_level(logging.INFO), pytest.raises(TimeoutError, match="migration_lock_timeout"):
        migration_lock.acquire_migration_lock(Connection(), timeout=0.5)
    assert elapsed[0] == 0.5
    assert "migration_lock_waiting" in caplog.text
    assert "migration_lock_timeout" in caplog.text


def test_release_startup_uses_packaged_head_not_environment(monkeypatch):
    from scope_guard.database import startup

    calls = []
    monkeypatch.setenv("SCOPE_GUARD_DATABASE_URL", "postgresql://user:x@localhost/test")
    monkeypatch.setenv("SCOPE_GUARD_MIGRATION_TARGET", "0007_nonblocking_llm")
    monkeypatch.setattr(startup, "wait_for_database", lambda value: None)
    monkeypatch.setattr(startup, "migrate_main", lambda args: calls.append(args) or 0)
    assert startup.main(["--database-url-env", "SCOPE_GUARD_DATABASE_URL"]) == 0
    assert calls == [
        ["migrate", "--database-url-env", "SCOPE_GUARD_DATABASE_URL", "--target", "head"]
    ]


@pytest.mark.parametrize("failure", ["database", "migration"])
def test_migration_failure_does_not_print_parameters(monkeypatch, capsys, failure):
    from sqlalchemy.exc import OperationalError

    from scope_guard.database import cli

    secret = "private-token-must-not-appear"
    monkeypatch.setenv("SCOPE_GUARD_DATABASE_URL", "postgresql://user:x@localhost/test")
    for key in ("PGPORT", "PGSERVICE", "PGSERVICEFILE", "PGHOSTADDR"):
        monkeypatch.delenv(key, raising=False)

    def unavailable(*args, **kwargs):
        if failure == "migration":
            raise KeyError(secret)
        raise OperationalError("secret SQL " + secret, {"password": secret}, RuntimeError(secret))

    monkeypatch.setattr(cli, "create_engine", unavailable)
    assert cli.main(["migrate", "--database-url-env", "SCOPE_GUARD_DATABASE_URL"]) == 1
    output = capsys.readouterr()
    assert secret not in output.out + output.err
    assert "database_operation_failed" in output.err
    assert "execution_id=" in output.err and "exit_code=1" in output.err
