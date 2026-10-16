"""Refresh proposals without reinterpreting a manually selected commercial value."""

from copy import deepcopy
from decimal import Decimal, InvalidOperation


def same_value(field, left, right):
    if left == right:
        return True
    if (
        field in ("estimatedHours", "additionalCost")
        and left not in (None, "")
        and right not in (None, "")
    ):
        try:
            return Decimal(str(left)) == Decimal(str(right))
        except InvalidOperation:
            pass
    return False


def merge_estimate(saved, suggestion):
    result = deepcopy(saved)
    previous = saved.get("aiValues", {})

    def untouched(field):
        return field in previous and same_value(field, saved.get(field), previous[field])

    manual_pair = (
        previous.get("manualPrice") == "true"
        or saved.get("noAdditionalCharge")
        or not all(untouched(field) for field in ("additionalCost", "currency"))
    )
    manual_effort = previous.get("manualEffort") == "true" or not untouched("estimatedHours")
    manual_rationale = previous.get("manualRationale") == "true" or (
        bool(saved.get("rationale")) and not untouched("rationale")
    )
    for field, value in suggestion.items():
        if field in ("additionalCost", "currency") and manual_pair:
            continue
        if field == "estimatedHours" and manual_effort:
            continue
        if field == "rationale" and (manual_pair or manual_effort):
            if not manual_rationale:
                result[field] = ""
            continue
        if untouched(field):
            result[field] = value
    result["aiValues"] = {**previous, **suggestion}
    for marker, manual in (
        ("manualPrice", manual_pair),
        ("manualEffort", manual_effort),
        ("manualRationale", manual_rationale),
    ):
        if manual:
            result["aiValues"][marker] = "true"
    return result
