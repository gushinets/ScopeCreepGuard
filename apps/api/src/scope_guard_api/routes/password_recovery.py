"""Public admission never looks up accounts or waits for SMTP."""

import json
import re
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request
from scope_guard.domain.auth.recovery import RecoveryLimited, RecoveryUnavailable
from scope_guard.domain.auth.tokens import InvalidAuthToken
from scope_guard.domain.auth.validation import AuthError, credentials
from starlette.responses import JSONResponse

from scope_guard_api.client_source import client_source
from scope_guard_api.contracts import ErrorResponse, OkResponse
from scope_guard_api.dependencies import recovery_service
from scope_guard_api.routes.auth import locale

router = APIRouter(prefix="/api/auth/password", tags=["auth"])
HEADERS = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


async def body(request):
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > 8192:
            raise AuthError("errors.requestBodyInvalid", 400)
    try:
        value = json.loads(content)
    except (ValueError, UnicodeError, RecursionError):
        raise AuthError("errors.requestBodyInvalid", 400) from None
    if not isinstance(value, dict):
        raise AuthError("errors.requestBodyInvalid", 400)
    return value


def failure(error):
    if isinstance(error, RecoveryLimited):
        return JSONResponse(
            {"error": "errors.passwordRecoveryLimited"},
            429,
            headers={**HEADERS, "Retry-After": str(error.retry_after)},
        )
    return JSONResponse({"error": "errors.requestFailed"}, 503, headers=HEADERS)


def schema(properties, required):
    return {
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"type": "object", "properties": properties, "required": required}
                }
            },
        }
    }


LOCALE = {"type": "string", "enum": ["ru", "en"]}
RESPONSES: dict[int | str, dict[str, Any]] = {
    status: {"model": ErrorResponse} for status in (400, 429, 503)
}


@router.post(
    "/request",
    status_code=202,
    response_model=OkResponse,
    responses=RESPONSES,
    openapi_extra=schema(
        {"email": {"type": "string", "maxLength": 320}, "locale": LOCALE}, ["email"]
    ),
)
async def request_recovery(request: Request):
    value = await body(request)
    language = locale(value)
    email = value.get("email")
    if (
        not isinstance(email, str)
        or len(email) > 320
        or any(0xD800 <= ord(c) <= 0xDFFF for c in email)
    ):
        raise AuthError("errors.invalidEmail", 400)
    email, _ = credentials({"email": email, "password": "validation-only"})
    if any(ord(c) < 32 or ord(c) == 127 for c in email):
        raise AuthError("errors.invalidEmail", 400)
    try:
        if not request.app.state.settings.public_app_url:
            raise RecoveryUnavailable()
        await recovery_service(request).request(email, language, await client_source(request))
    except (RecoveryLimited, RecoveryUnavailable, TimeoutError) as error:
        return failure(error)
    return JSONResponse({"ok": True}, 202, headers=HEADERS)


@router.post(
    "/reset",
    response_model=OkResponse,
    responses=RESPONSES,
    openapi_extra=schema(
        {
            "userId": {"type": "string", "format": "uuid"},
            "token": {"type": "string", "minLength": 20, "maxLength": 128, "writeOnly": True},
            "password": {"type": "string", "writeOnly": True},
            "locale": LOCALE,
        },
        ["userId", "token", "password"],
    ),
)
async def reset_password(request: Request):
    try:
        await recovery_service(request).reset_limit(await client_source(request))
        value = await body(request)
        language = locale(value)
        try:
            owner = UUID(value.get("userId", ""))
            raw = value.get("token")
            if not isinstance(raw, str) or not re.fullmatch(r"[A-Za-z0-9_-]{20,128}", raw):
                raise InvalidAuthToken()
        except (ValueError, TypeError, AttributeError, InvalidAuthToken):
            raise AuthError("errors.passwordRecoveryInvalid", 400) from None
        password = value.get("password")
        if (
            not isinstance(password, str)
            or len(password.encode("utf-8", errors="surrogatepass")) > 4096
        ):
            raise AuthError("errors.passwordRequired", 400)
        try:
            await recovery_service(request).reset_password(owner, raw, password, language)
        except InvalidAuthToken:
            raise AuthError("errors.passwordRecoveryInvalid", 400) from None
    except (RecoveryLimited, RecoveryUnavailable, TimeoutError) as error:
        return failure(error)
    return JSONResponse({"ok": True}, headers=HEADERS)
