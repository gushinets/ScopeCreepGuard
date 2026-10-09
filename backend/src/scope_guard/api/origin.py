"""Supplied browser Origins must match explicitly configured public origins."""

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from scope_guard.api.errors import ErrorCode, json_error


class OriginMiddleware:
    def __init__(self, app: ASGIApp, allowed_origins: tuple[str, ...]):
        self.app, self.allowed_origins = app, allowed_origins

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] == "http"
            and scope["path"].startswith("/api/")
            and scope["method"] in {"POST", "PUT", "PATCH", "DELETE"}
        ):
            headers = Headers(scope=scope)
            origins = headers.getlist("origin")
            if origins and (len(origins) != 1 or origins[0] not in self.allowed_origins):
                await json_error(ErrorCode.request_failed, 403)(scope, receive, send)
                return
        await self.app(scope, receive, send)
