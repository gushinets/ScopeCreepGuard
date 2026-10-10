from fastapi import Request

from scope_guard.modules.analysis.domain import LocaleResolution


def resolve_locale(request: Request) -> LocaleResolution:
    value = request.cookies.get("locale") or "ru"
    return LocaleResolution(value, failed=value not in ("en", "ru"))
