"""Opaque signed browser cookie; authentication still resolves the user independently."""

import hashlib
import hmac
import secrets

from scope_guard.services.activity.context import browser_key
from starlette.middleware.base import BaseHTTPMiddleware

BROWSER_COOKIE = "scg_browser"


class ActivityContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        secret = request.app.state.settings.auth_secret
        if not secret:
            return await call_next(request)
        secret = secret.get_secret_value().encode()
        cookie = request.cookies.get(BROWSER_COOKIE, "")
        parts = cookie.split(".")
        valid = (
            len(parts) == 2
            and len(parts[0]) == 64
            and hmac.compare_digest(
                hmac.new(
                    secret, ("product-browser:" + parts[0]).encode(), hashlib.sha256
                ).hexdigest(),
                parts[1],
            )
        )
        if not valid:
            nonce = secrets.token_hex(32)
            signature = hmac.new(
                secret, ("product-browser:" + nonce).encode(), hashlib.sha256
            ).hexdigest()
            cookie = nonce + "." + signature
        token = browser_key.set(hashlib.sha256(cookie.encode()).hexdigest())
        try:
            response = await call_next(request)
        finally:
            browser_key.reset(token)
        hydrate = request.method == "GET" and request.url.path == "/api/auth/me"
        if not valid and response.status_code < 400 and (request.method != "GET" or hydrate):
            response.set_cookie(
                BROWSER_COOKIE,
                cookie,
                httponly=True,
                samesite="lax",
                secure=request.app.state.settings.production,
                path="/",
            )
        return response
