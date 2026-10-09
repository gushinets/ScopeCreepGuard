import asyncio

import pytest


def test_url_alias_priority_and_secret_representation(monkeypatch):
    from scope_guard.core.config import Settings

    monkeypatch.setenv("DATABASE_URL", "postgres://old:secret@localhost/old")
    monkeypatch.setenv("SCOPE_GUARD_DATABASE_URL", "postgres://new:private@localhost/new")
    settings = Settings(_env_file=None)
    assert settings.database_url.get_secret_value().endswith("/new")
    assert "private" not in repr(settings)


def test_normalization_rejects_other_drivers_without_credentials():
    from scope_guard.infrastructure.database.session import normalize_url

    assert normalize_url("postgres://user:secret@localhost/test").drivername == "postgresql+psycopg"
    with pytest.raises(ValueError, match="unsupported_database_url") as failure:
        normalize_url("mysql://user:secret@localhost/test")
    assert "secret" not in str(failure.value)


def test_missing_database_does_not_create_pool():
    from scope_guard.core.config import Settings
    from scope_guard.infrastructure.database.session import create_database

    assert create_database(Settings(_env_file=None, database_url=None)) is None


def test_configured_unreachable_database_is_lazy_and_can_close():
    from scope_guard.core.config import Settings
    from scope_guard.infrastructure.database.session import create_database

    async def exercise():
        database = create_database(
            Settings(_env_file=None, database_url="postgresql://x:x@127.0.0.1:1/test")
        )
        assert database.engine.pool.checkedout() == 0
        await database.close()

    asyncio.run(exercise())


def test_invalid_database_configuration_preserves_independent_liveness():
    from scope_guard.core.config import Settings
    from scope_guard.infrastructure.database.session import create_database

    assert create_database(Settings(_env_file=None, database_url="unavailable")) is None


def test_documented_loop_factory_is_psycopg_compatible():
    from scope_guard.infrastructure.database.session import event_loop

    loop = event_loop()
    try:
        assert isinstance(loop, asyncio.SelectorEventLoop)
    finally:
        loop.close()
