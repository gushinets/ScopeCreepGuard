import hashlib
import hmac
from datetime import UTC, datetime
from email.utils import format_datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from scope_guard.services.auth.ports import SESSION_COOKIE_NAME, SESSION_MAX_AGE_SECONDS
from scope_guard.services.auth.use_cases import AuthError, AuthService
from starlette.responses import JSONResponse

from scope_guard_api import bootstrap
from scope_guard_api.client_source import client_source
from scope_guard_api.contracts import (
    AuthResponse,
    EmailConfirmationResponse,
    ErrorResponse,
    OkResponse,
)
from scope_guard_api.dependencies import auth_service
from scope_guard_api.errors import read_json_object

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)

AuthDependency = Annotated[AuthService, Depends(auth_service)]
credentials_request = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "required": ["email", "password"],
                    "properties": {
                        "email": {"type": "string"},
                        "password": {"type": "string"},
                        "locale": {"type": "string", "enum": ["ru", "en"]},
                    },
                }
            }
        },
    }
}


def session_cookie(response: JSONResponse, request: Request, token: str, max_age: int) -> None:
    # Match Next cookie serialization, including seven-day Expires and logout without Expires.
    cookie = f"{SESSION_COOKIE_NAME}={token}; Path=/"
    if max_age:
        expires = datetime.fromtimestamp(request.app.state.clock() + max_age, UTC)
        cookie += "; Expires=" + format_datetime(expires, usegmt=True)
    cookie += f"; Max-Age={max_age}"
    if request.app.state.settings.production:
        cookie += "; Secure"
    cookie += "; HttpOnly; SameSite=lax"
    response.headers.append("set-cookie", cookie)


@router.post(
    "/register", status_code=201, response_model=AuthResponse, openapi_extra=credentials_request
)
async def register(request: Request, service: AuthDependency):
    from scope_guard.services.auth.confirmation import ResendLimited

    body = await read_json_object(request)
    language = locale(body)
    user, token = await service.register(body)
    state = {"status": "not_attempted", "retryAfter": 0}
    if user.get("workspaceAccess") == "email_confirmation_required":
        try:
            state = await bootstrap.confirmation_service(request).send(
                user, language, await source(request)
            )
        except ResendLimited as error:
            state = {"status": "not_attempted", "retryAfter": error.retry_after}
        except Exception:
            # Account commit already succeeded. Do not lose the recoverable
            # identity due to issuance/accounting/provider failure.
            state = {"status": "unknown", "retryAfter": 60}
    response = JSONResponse({"user": user, "emailConfirmation": state}, status_code=201)
    session_cookie(response, request, token, SESSION_MAX_AGE_SECONDS)
    return response


@router.post("/login", response_model=AuthResponse, openapi_extra=credentials_request)
async def login(request: Request, service: AuthDependency):
    user, token = await service.login(await read_json_object(request))
    if (
        getattr(request.app.state, "database", None) is not None
        and user.get("workspaceAccess") != "email_confirmation_required"
    ):
        from uuid import UUID

        from scope_guard_api.dependencies import profile_service

        await profile_service(request).observe(UUID(user["id"]))
    response = JSONResponse(await identity_response(request, user))
    session_cookie(response, request, token, SESSION_MAX_AGE_SECONDS)
    return response


@router.post("/logout", response_model=OkResponse)
async def logout(request: Request):
    response = JSONResponse({"ok": True})
    session_cookie(response, request, "", 0)
    return response


@router.get("/me", response_model=AuthResponse)
async def me(request: Request, service: AuthDependency):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    try:
        return JSONResponse(
            await identity_response(request, await service.me(token)),
            headers={"Cache-Control": "no-store"},
        )
    except AuthError as error:
        if error.status != 401:
            raise
        response = JSONResponse({"error": error.code}, status_code=401)
        if token:
            session_cookie(response, request, "", 0)
        return response


def locale(body: dict) -> str:
    value = body.get("locale", "en")
    if value not in ("ru", "en"):
        raise AuthError("errors.localeInvalid", 400)
    return value


async def source(request: Request) -> str:
    address = await client_source(request)
    secret = request.app.state.settings.auth_secret
    key = secret.get_secret_value() if secret else ""
    return hmac.new(
        key.encode(), ("email-confirmation-source:" + address).encode(), hashlib.sha256
    ).hexdigest()


async def identity_response(request: Request, user: dict) -> dict:
    response = {"user": user}
    if user.get("workspaceAccess") == "email_confirmation_required":
        response["emailConfirmation"] = await bootstrap.confirmation_service(
            request
        ).attempts.status(UUID(user["id"]), await source(request))
    return response


@router.post(
    "/email/resend",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"locale": {"type": "string", "enum": ["ru", "en"]}},
                    }
                }
            },
        }
    },
    response_model=EmailConfirmationResponse,
    responses={429: {"model": ErrorResponse}},
)
async def resend(request: Request, service: AuthDependency):
    from scope_guard.services.auth.confirmation import ResendLimited

    user = await service.me(request.cookies.get(SESSION_COOKIE_NAME))
    language = locale(await read_json_object(request))
    try:
        state = await bootstrap.confirmation_service(request).send(
            user, language, await source(request)
        )
    except ResendLimited as error:
        return JSONResponse(
            {"error": error.code},
            status_code=429,
            headers={"Retry-After": str(error.retry_after), "Cache-Control": "no-store"},
        )
    return JSONResponse({"emailConfirmation": state}, headers={"Cache-Control": "no-store"})


@router.post(
    "/email/confirm",
    response_model=OkResponse,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["userId", "token"],
                        "properties": {
                            "userId": {"type": "string", "format": "uuid"},
                            "token": {
                                "type": "string",
                                "minLength": 20,
                                "maxLength": 128,
                                "writeOnly": True,
                            },
                        },
                    }
                }
            },
        }
    },
)
async def confirm(request: Request):
    from scope_guard.domain.auth.tokens import InvalidAuthToken

    body = await read_json_object(request)
    try:
        user_id = UUID(body.get("userId", ""))
        raw = body.get("token")
        if not isinstance(raw, str) or not 20 <= len(raw) <= 128:
            raise InvalidAuthToken()
        await bootstrap.confirmation_service(request).tokens.confirm_email(user_id, raw)
    except (InvalidAuthToken, ValueError, TypeError, AttributeError):
        raise AuthError("errors.emailConfirmationInvalid", 400) from None
    return JSONResponse({"ok": True}, headers={"Cache-Control": "no-store"})
