"""Self-service professional fields. Ownership and exclusion flags are server owned."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from scope_guard.domain.drafts.workflow import WorkflowError

PROFILE_FIELDS = {
    "displayName": "display_name",
    "businessName": "business_name",
    "providerName": "provider_name",
    "profession": "profession",
    "status": "status",
}
PREFERENCE_FIELDS = {
    "locale": "locale",
    "timezone": "timezone",
    "preferredTone": "preferred_tone",
    "defaultCurrency": "default_currency",
}


def validate_changes(changes):
    if (
        not isinstance(changes, dict)
        or not changes
        or changes.keys() - (PROFILE_FIELDS.keys() | {"preferences"})
    ):
        raise WorkflowError("profileInvalid")
    choices = {
        "status": {"active", "inactive"},
        "locale": {"ru", "en"},
        "preferredTone": {"warm", "neutral", "firm"},
        "defaultCurrency": {"RUB", "USD", "EUR"},
    }
    preferences = changes.get("preferences", {})
    if not isinstance(preferences, dict) or preferences.keys() - PREFERENCE_FIELDS.keys():
        raise WorkflowError("profileInvalid")
    for key, value in {
        **{k: v for k, v in changes.items() if k != "preferences"},
        **preferences,
    }.items():
        if value is None and key != "status":
            continue
        if not isinstance(value, str) or len(value) > (100 if key == "timezone" else 250):
            raise WorkflowError("profileInvalid")
        if key in choices and value not in choices[key]:
            raise WorkflowError("profileInvalid")
        if key == "timezone":
            try:
                ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError):
                raise WorkflowError("profileInvalid") from None
    return changes
