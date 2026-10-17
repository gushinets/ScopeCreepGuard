"""Authoritative commercial facts shared by admission, prompting and diagnostics."""


def current_commercial_terms(facts):
    """Use saved fields even when empty; only absent agreements use AI estimates."""
    if "currentCommercialTerms" in facts:
        return facts["currentCommercialTerms"]
    order = (facts.get("document") or {}).get("changeOrder")
    saved = order is not None
    analysis = facts.get("analysis") or {}
    values = order if saved else (analysis.get("estimate") or analysis)
    return {
        "source": "savedAgreement" if saved else "preliminaryEstimate",
        "preliminary": not saved,
        **{
            key: values.get(key)
            for key in (
                "estimatedHours",
                "additionalCost",
                "currency",
                "timelineImpact",
                "endDate",
                "additionalTerms",
            )
        },
        "noAdditionalCharge": bool(values.get("noAdditionalCharge", False)),
    }
