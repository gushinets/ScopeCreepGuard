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


@pytest.mark.parametrize(
    "primary,alias,expected",
    [
        (None, None, "gpt-6-luna"),
        ("configured-model", "legacy-model", "configured-model"),
        (None, "legacy-model", "legacy-model"),
    ],
)
def test_openai_model_environment(monkeypatch, primary, alias, expected):
    from scope_guard.core.config import Settings

    for name, value in (("SCOPE_GUARD_OPENAI_MODEL", primary), ("OPENAI_MODEL", alias)):
        monkeypatch.delenv(name, raising=False)
        if value is not None:
            monkeypatch.setenv(name, value)
    assert Settings(_env_file=None).openai_model == expected


@pytest.mark.parametrize("name", ["SCOPE_GUARD_OPENAI_MODEL", "OPENAI_MODEL"])
@pytest.mark.parametrize("value", ["", " \t\n"])
def test_empty_openai_model_is_rejected(monkeypatch, name, value):
    from scope_guard.core.config import Settings

    monkeypatch.delenv("SCOPE_GUARD_OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.setenv(name, value)
    if name == "SCOPE_GUARD_OPENAI_MODEL":
        monkeypatch.setenv("OPENAI_MODEL", "legacy-model")
    with pytest.raises(ValidationError, match="openai_model must not be empty or whitespace-only"):
        Settings(_env_file=None)


def test_composition_root_passes_configured_model(monkeypatch):
    from types import SimpleNamespace

    from scope_guard_api import bootstrap

    from scope_guard.core.config import Settings

    calls = []
    monkeypatch.setattr(bootstrap, "OpenAIGeneration", lambda *args, **kwargs: calls.append(kwargs))
    monkeypatch.setenv("SCOPE_GUARD_OPENAI_MODEL", "configured-model")
    bootstrap.configure_app(SimpleNamespace(state=SimpleNamespace()), Settings(_env_file=None))
    assert calls == [{"model": "configured-model"}]
