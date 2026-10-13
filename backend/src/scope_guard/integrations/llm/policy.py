"""Freeze a known local tariff or an explicit conservative operator bound."""

from decimal import Decimal

import litellm


def policy(settings):
    model = settings.openai_model.removeprefix("openai/")
    tariff = litellm.model_cost.get(model, {})
    rate_in = settings.llm_input_rate_bound or tariff.get("input_cost_per_token")
    rate_out = settings.llm_output_rate_bound or tariff.get("output_cost_per_token")
    if not rate_in or not rate_out:
        rate_in = rate_out = None
    return {
        "version": "workflow-policy-v1",
        "model": model,
        "maxCalls": 12,
        "durationSeconds": 180,
        "maxCost": str(settings.llm_max_cost),
        "inputRate": str(Decimal(str(rate_in))) if rate_in is not None else None,
        "outputRate": str(Decimal(str(rate_out))) if rate_out is not None else None,
        "priceSource": "operator-conservative-bound"
        if settings.llm_input_rate_bound and settings.llm_output_rate_bound
        else "litellm-1.89.3-local-tariff",
        "nativeSchema": True,
        "currency": "USD",
    }
