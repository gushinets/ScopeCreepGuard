"""Existing JOSE HS256 session format; proof keys remain separately derived."""

import base64
import hashlib
import hmac
import json
import re
import time
from collections.abc import Callable

SESSION_COOKIE_NAME = "scg_session"
SESSION_MAX_AGE_SECONDS = 604800


def encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def decode(value: str) -> bytes:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("invalid_base64url")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class Sessions:
    def __init__(self, secret: str, clock: Callable[[], float] = time.time):
        self.key = secret.encode("utf-8")
        self.clock = clock

    def issue(self, user: dict[str, str]) -> str:
        now = int(self.clock())
        payload = {
            "email": user["email"],
            "sub": user["id"],
            "iat": now,
            "exp": now + SESSION_MAX_AGE_SECONDS,
        }
        parts = [
            encode(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode())
            for value in ({"alg": "HS256"}, payload)
        ]
        signing_input = ".".join(parts)
        return (
            signing_input
            + "."
            + encode(hmac.digest(self.key, signing_input.encode(), hashlib.sha256))
        )

    def verify(self, token: str) -> dict[str, str] | None:
        try:
            header, payload, signature = token.split(".")
            protected = json.loads(decode(header))
            if not isinstance(protected, dict) or protected.get("alg") != "HS256":
                return None
            if "crit" in protected or protected.get("b64") is False:
                return None
            expected = hmac.digest(self.key, f"{header}.{payload}".encode("ascii"), hashlib.sha256)
            if not hmac.compare_digest(expected, decode(signature)):
                return None
            claims = json.loads(decode(payload))
            if not isinstance(claims, dict):
                return None
            if not isinstance(claims.get("sub"), str) or not isinstance(claims.get("email"), str):
                return None
            if type(claims.get("iat")) is not int or type(claims.get("exp")) is not int:
                return None
            if claims["exp"] <= self.clock():
                return None
            if "nbf" in claims and (
                type(claims["nbf"]) not in (int, float) or not claims["nbf"] <= self.clock()
            ):
                return None
            return {"id": claims["sub"], "email": claims["email"]}
        except (ValueError, TypeError, UnicodeError, KeyError, OverflowError):
            return None
