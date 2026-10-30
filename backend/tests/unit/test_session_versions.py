import hashlib
import hmac
import json

import pytest

from scope_guard.integrations.auth.sessions import Sessions, encode


def signed(extra):
    claims = {"sub": "owner", "email": "a@b.test", "iat": 1, "exp": 200, **extra}
    value = ".".join(encode(json.dumps(v).encode()) for v in ({"alg": "HS256"}, claims))
    return value + "." + encode(hmac.digest(b"synthetic", value.encode(), hashlib.sha256))


@pytest.mark.parametrize("version", [True, False, "0", -1, 0.0, None, [], {}])
def test_malformed_version(version):
    assert Sessions("synthetic", lambda: 100).verify(signed({"session_version": version})) is None


def test_missing_and_current_version():
    codec = Sessions("synthetic", lambda: 100)
    assert codec.verify(signed({}))["session_version"] == 0
    user = {"id": "owner", "email": "a@b.test", "session_version": 4}
    assert codec.verify(codec.issue(user))["session_version"] == 4
