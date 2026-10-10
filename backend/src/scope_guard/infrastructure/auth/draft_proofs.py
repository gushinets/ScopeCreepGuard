"""Domain-separated HS256 tokens interoperable with the transitional JOSE saver."""

import base64
import hmac
import json
import math
import re

from scope_guard.core.js_compat import stringify, utf16_length
from scope_guard.modules.analysis.domain import DraftProofBinding, DraftProofClaims, freeze, thaw
from scope_guard.modules.analysis.normalization import parse_snapshot
from scope_guard.modules.analysis.serialization import analysis_to_wire

VERSION = "scg-draft-proof-v1"
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def decode(segment: str) -> bytes:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", segment):
        raise ValueError("invalid_draft_proof")
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


class DraftProofs:
    def __init__(self, secret: str, clock):
        if not secret:
            raise ValueError("auth_secret_missing")
        self._key = hmac.digest(secret.encode("utf-8"), VERSION.encode("utf-8"), "sha256")
        self._clock = clock

    def issue(self, claims: DraftProofClaims) -> str:
        b = claims.binding
        now = math.floor(self._clock())
        payload = {
            "userId": b.user_id,
            "projectId": b.project_id,
            "request": b.request,
            "locale": b.locale,
            "analysisSnapshot": analysis_to_wire(claims.analysis_snapshot),
            "projectSnapshot": thaw(claims.project_snapshot),
            "version": VERSION,
            "iss": "scope-creep-guard",
            "aud": "draft-creation",
            "sub": b.user_id,
            "iat": now,
            "exp": now + 3600,
        }
        parts = [
            encode(stringify({"alg": "HS256", "typ": VERSION}).encode()),
            encode(stringify(payload).encode()),
        ]
        message = ".".join(parts)
        return message + "." + encode(hmac.digest(self._key, message.encode("ascii"), "sha256"))

    def verify(self, token: object, expected: DraftProofBinding) -> DraftProofClaims:
        try:
            if not isinstance(token, str) or utf16_length(token) > 2_000_000:
                raise ValueError
            header_part, payload_part, signature = token.split(".")
            actual = hmac.digest(
                self._key, (header_part + "." + payload_part).encode("ascii"), "sha256"
            )
            if not hmac.compare_digest(actual, decode(signature)):
                raise ValueError

            def invalid_constant(_):
                raise ValueError

            header = json.loads(decode(header_part), parse_constant=invalid_constant)
            payload = json.loads(decode(payload_part), parse_constant=invalid_constant)
            if not isinstance(header, dict) or not isinstance(payload, dict):
                raise ValueError
            if (
                header.get("alg") != "HS256"
                or header.get("typ") != VERSION
                or "crit" in header
                or header.get("b64") is False
            ):
                raise ValueError
            now = math.floor(self._clock())
            iat, exp = payload["iat"], payload["exp"]
            if any(
                type(n) not in (int, float) or not math.isfinite(n) or int(n) != n
                for n in (iat, exp)
            ):
                raise ValueError
            if iat > now or exp <= now or exp <= iat or exp - iat > 3600:
                raise ValueError
            if "nbf" in payload and (
                type(payload["nbf"]) not in (int, float)
                or not math.isfinite(payload["nbf"])
                or payload["nbf"] > now
            ):
                raise ValueError
            aud = payload.get("aud")
            if payload.get("iss") != "scope-creep-guard" or not (
                aud == "draft-creation" or isinstance(aud, list) and "draft-creation" in aud
            ):
                raise ValueError
            b = expected
            for key, value in (
                ("sub", b.user_id),
                ("userId", b.user_id),
                ("projectId", b.project_id),
                ("request", b.request),
                ("locale", b.locale),
                ("version", VERSION),
            ):
                if payload.get(key) != value:
                    raise ValueError
            if b.locale not in ("en", "ru") or not UUID_PATTERN.fullmatch(b.project_id):
                raise ValueError
            snapshot = payload.get("projectSnapshot")
            if (
                not isinstance(snapshot, dict)
                or type(snapshot.get("version")) not in (int, float)
                or snapshot["version"] != 1
            ):
                raise ValueError
            return DraftProofClaims(
                b, parse_snapshot(payload.get("analysisSnapshot"), b.locale), freeze(snapshot)
            )
        except (
            ValueError,
            TypeError,
            KeyError,
            OverflowError,
            AttributeError,
            UnicodeError,
        ) as error:
            raise ValueError("invalid_draft_proof") from error
