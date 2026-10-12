from datetime import UTC, datetime
from email.utils import format_datetime

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from scope_guard_api.contracts import ErrorResponse, OkResponse
from scope_guard_api.errors import ApiError, ErrorCode, read_json_object

router = APIRouter(tags=["locale"], responses={400: {"model": ErrorResponse}})
MAX_AGE = 60 * 60 * 24 * 365
locale_contract = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "required": ["locale"],
                    "properties": {"locale": {"type": "string", "enum": ["en", "ru"]}},
                }
            }
        },
    }
}


@router.post("/api/locale", response_model=OkResponse, openapi_extra=locale_contract)
async def set_locale(request: Request):
    body = await read_json_object(request)
    if body.get("locale") not in ("en", "ru"):
        raise ApiError(ErrorCode.locale_invalid)
    response = JSONResponse({"ok": True})
    expires = datetime.fromtimestamp(request.app.state.clock() + MAX_AGE, UTC)
    cookie = (
        f"locale={body['locale']}; Path=/; Expires={format_datetime(expires, usegmt=True)}; "
        f"Max-Age={MAX_AGE}"
    )
    if request.app.state.settings.production:
        cookie += "; Secure"
    cookie += "; SameSite=lax"
    response.headers.append("set-cookie", cookie)
    return response
