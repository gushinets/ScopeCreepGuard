from datetime import UTC, datetime
from email.utils import format_datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from starlette.responses import JSONResponse

from scope_guard.api.contracts import AuthResponse, ErrorResponse, OkResponse
from scope_guard.api.dependencies import auth_service
from scope_guard.api.errors import read_json_object
from scope_guard.infrastructure.auth.sessions import SESSION_COOKIE_NAME, SESSION_MAX_AGE_SECONDS
from scope_guard.modules.auth.use_cases import AuthError, AuthService

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
                    "properties": {"email": {"type": "string"}, "password": {"type": "string"}},
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
    user, token = await service.register(await read_json_object(request))
    response = JSONResponse({"user": user}, status_code=201)
    session_cookie(response, request, token, SESSION_MAX_AGE_SECONDS)
    return response


@router.post("/login", response_model=AuthResponse, openapi_extra=credentials_request)
async def login(request: Request, service: AuthDependency):
    user, token = await service.login(await read_json_object(request))
    response = JSONResponse({"user": user})
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
        return JSONResponse({"user": await service.me(token)})
    except AuthError as error:
        if error.status != 401:
            raise
        response = JSONResponse({"error": error.code}, status_code=401)
        if token:
            session_cookie(response, request, "", 0)
        return response
