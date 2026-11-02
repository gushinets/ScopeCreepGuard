"""Tariff attribution follows the installed SDK; saved policy remains frozen."""

from copy import deepcopy
from decimal import Decimal
from importlib.metadata import version

from scope_guard.core.config import Settings
from scope_guard.integrations.llm.policy import policy


def test_tariff_uses_installed_version_and_preserves_saved_policy(monkeypatch):
    settings = Settings(_env_file=None, openai_model="gpt-4o-mini")
    saved = policy(settings)
    original = deepcopy(saved)
    monkeypatch.setattr(
        "scope_guard.integrations.llm.policy.version", lambda name: "99.0-test", raising=False
    )
    current = policy(settings)
    assert current["priceSource"] == "litellm-99.0-test-local-tariff"
    assert saved == original
    assert saved["priceSource"] == f"litellm-{version('litellm')}-local-tariff"


def test_operator_rates_keep_operator_attribution():
    settings = Settings(
        _env_file=None,
        openai_model="gpt-4o-mini",
        llm_input_rate_bound=Decimal("0.01"),
        llm_output_rate_bound=Decimal("0.02"),
    )
    frozen = policy(settings)
    assert frozen["priceSource"] == "operator-conservative-bound"
    assert frozen["inputRate"] == "0.01"
    assert frozen["outputRate"] == "0.02"
