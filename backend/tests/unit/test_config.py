import pytest
from pydantic import ValidationError


def test_settings_default_without_external_configuration(monkeypatch):
    monkeypatch.delenv("SCOPE_GUARD_LOG_LEVEL", raising=False)
    from scope_guard.core.config import Settings

    assert Settings(_env_file=None).log_level == "INFO"


def test_log_level_can_be_configured(monkeypatch):
    monkeypatch.setenv("SCOPE_GUARD_LOG_LEVEL", "DEBUG")
    from scope_guard.core.config import Settings

    assert Settings(_env_file=None).log_level == "DEBUG"


def test_invalid_log_level_is_rejected(monkeypatch):
    monkeypatch.setenv("SCOPE_GUARD_LOG_LEVEL", "not-a-level")
    from scope_guard.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
