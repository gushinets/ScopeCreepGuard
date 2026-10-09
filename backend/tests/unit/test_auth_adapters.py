import asyncio
import hashlib
import hmac
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "contracts/compatibility/any-640/auth.json"


def test_bidirectional_jose_session_and_bcryptjs_hashes():
    from scope_guard.infrastructure.auth.passwords import Passwords
    from scope_guard.infrastructure.auth.sessions import Sessions

    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    codec = Sessions(
        "any640-synthetic-contract-secret-at-least-32-characters", lambda: fixture["now"]
    )
    assert codec.verify(fixture["token"]) == fixture["user"]
    token = codec.issue(fixture["user"])
    assert token == fixture["token"]

    async def passwords():
        adapter = Passwords()
        output = []
        for entry in fixture["passwords"]:
            assert await adapter.verify(entry["password"], entry["hash"])
            assert await adapter.verify(entry["password"], entry["hash"].replace("$2b$", "$2a$"))
            assert await adapter.verify(entry["password"], entry["hash"].replace("$2b$", "$2y$"))
            assert not await adapter.verify("wrong-password", entry["hash"])
            hashed = await adapter.hash(entry["password"])
            assert hashed.startswith("$2b$12$")
            output.append({"password": entry["password"], "hash": hashed})
        return output

    result = subprocess.run(
        ["node", "scripts/auth-compatibility.mjs"],
        cwd=ROOT / "frontend",
        input=json.dumps({"token": token, "passwords": asyncio.run(passwords())}),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, "cross_runtime_auth_failed"


@pytest.mark.parametrize("token", ["", "broken", "a.b.c", "eyJhbGciOiJub25lIn0.e30."])
def test_sessions_reject_malformed_tokens(token):
    from scope_guard.infrastructure.auth.sessions import Sessions

    assert Sessions("synthetic-secret", lambda: 100).verify(token) is None


def test_session_expiry_and_tampering():
    from scope_guard.infrastructure.auth.sessions import Sessions

    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    key = "any640-synthetic-contract-secret-at-least-32-characters"
    assert Sessions(key, lambda: fixture["now"] + 604800).verify(fixture["token"]) is None
    assert Sessions("wrong-secret", lambda: fixture["now"]).verify(fixture["token"]) is None
    header, payload, signature = fixture["token"].split(".")
    assert (
        Sessions(key, lambda: fixture["now"]).verify(f"{header}.{payload}.{signature[:-2]}aa")
        is None
    )


@pytest.mark.parametrize(
    "header,claims",
    [
        ({"alg": "HS512"}, {"sub": "owner", "email": "a@b.test", "iat": 1, "exp": 200}),
        (
            {"alg": "HS256", "crit": ["unknown"]},
            {"sub": "owner", "email": "a@b.test", "iat": 1, "exp": 200},
        ),
        ({"alg": "HS256"}, {"sub": "owner", "email": "a@b.test", "exp": 200}),
        ({"alg": "HS256"}, {"sub": "owner", "email": "a@b.test", "iat": 1, "exp": True}),
        ({"alg": "HS256"}, {"sub": "owner", "email": "a@b.test", "iat": 1, "exp": 200, "nbf": 101}),
    ],
)
def test_signed_invalid_session_claims_and_headers(header, claims):
    from scope_guard.infrastructure.auth.sessions import Sessions, encode

    signing_input = ".".join(encode(json.dumps(value).encode()) for value in (header, claims))
    token = (
        signing_input
        + "."
        + encode(hmac.digest(b"synthetic", signing_input.encode(), hashlib.sha256))
    )
    assert Sessions("synthetic", lambda: 100).verify(token) is None
