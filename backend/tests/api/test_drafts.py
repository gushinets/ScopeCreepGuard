import hmac
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from scope_guard.api.dependencies import current_owner, draft_service
from scope_guard.core.config import Settings
from scope_guard.infrastructure.auth.draft_proofs import DraftProofs, decode, encode
from scope_guard.main import create_app
from scope_guard.modules.analysis.domain import DraftProofBinding, DraftProofClaims, freeze
from scope_guard.modules.analysis.normalization import parse_snapshot
from scope_guard.modules.drafts.use_cases import DraftError

OWNER = "11111111-1111-4111-8111-111111111111"


@pytest.mark.parametrize(
    "target,key,value",
    [
        ("payload", "exp", 1000),
        ("payload", "iat", 1001),
        ("payload", "iss", "other"),
        ("payload", "aud", "other"),
        ("payload", "version", "other"),
        ("payload", "sub", "other"),
        ("payload", "userId", "other"),
        ("payload", "projectId", "other"),
        ("payload", "request", "other"),
        ("payload", "locale", "ru"),
        ("header", "typ", "JWT"),
        ("header", "alg", "HS512"),
        ("key", "secret", "other"),
    ],
)
def test_every_invalid_proof_maps_before_document_or_persistence(target, key, value):
    data = json.loads((Path(__file__).parents[1] / "fixtures/contracts.json").read_text())
    app = create_app(
        Settings(_env_file=None, auth_secret=SecretStr("synthetic")), clock=lambda: 1000
    )
    app.dependency_overrides[current_owner] = lambda: {"id": OWNER}
    binding = DraftProofBinding(OWNER, OWNER, "Add another page", "en")
    proof = DraftProofs("synthetic", lambda: 1000).issue(
        DraftProofClaims(binding, parse_snapshot(data["analysis"], "en"), freeze(data["snapshot"]))
    )
    header, payload, _ = proof.split(".")
    if target != "key":
        raw = json.loads(decode(header if target == "header" else payload))
        raw[key] = value
        segment = encode(json.dumps(raw).encode())
        if target == "header":
            header = segment
        else:
            payload = segment
    message = header + "." + payload
    secret = value if target == "key" else "synthetic"
    signature = hmac.digest(
        hmac.digest(secret.encode(), b"scg-draft-proof-v1", "sha256"), message.encode(), "sha256"
    )
    proof = message + "." + encode(signature)
    response = TestClient(app).post(
        "/api/drafts",
        json={
            "projectId": OWNER,
            "idempotencyKey": OWNER,
            "request": "Add another page",
            "locale": "en",
            "proof": proof,
            "draftDocument": {},
        },
    )
    assert response.status_code == 400
    assert response.json() == {"error": "errors.draftProofInvalid"}


def test_lookup_precedes_put_body_and_database_failures_keep_endpoint_codes():
    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[current_owner] = lambda: {"id": OWNER}

    class Service:
        async def list(self, _):
            raise RuntimeError("injected")

        async def get(self, *_):
            raise RuntimeError("injected")

        async def update(self, *_):
            raise DraftError("draftNotFound", 404)

    app.dependency_overrides[draft_service] = Service
    client = TestClient(app)
    for path in ("/api/drafts", "/api/drafts/" + OWNER):
        r = client.get(path)
        assert r.status_code == 500 and r.json() == {"error": "errors.draftLoadFailed"}
        assert r.headers["cache-control"] == "private, no-store"
    for identifier in (OWNER, "malformed"):
        r = client.put("/api/drafts/" + identifier, content="[")
        assert r.status_code == 404 and r.json() == {"error": "errors.draftNotFound"}
    r = client.post("/api/drafts", json={"proof": "bad", "draftDocument": {}})
    assert r.status_code == 400 and r.json() == {"error": "errors.requestBodyInvalid"}


def test_origin_precedes_auth_and_openapi_documents_all_methods():
    app = create_app(Settings(_env_file=None, allowed_origins=("https://allowed.test",)))
    client = TestClient(app)
    for method, path in (("POST", "/api/drafts"), ("PUT", "/api/drafts/" + OWNER)):
        r = client.request(method, path, json={}, headers={"origin": "https://foreign.test"})
        assert r.status_code == 403 and r.json() == {"error": "errors.requestFailed"}
    paths = app.openapi()["paths"]
    assert set(paths["/api/drafts"]) == {"get", "post"}
    assert set(paths["/api/drafts/{id}"]) == {"get", "put"}
    assert {"200", "201"} <= set(paths["/api/drafts"]["post"]["responses"])


def test_encoded_slash_ids_follow_auth_then_uniform_private_not_found():
    app = create_app(Settings(_env_file=None))
    client = TestClient(app)
    for path in ("/api/drafts/a%2Fb", "/api/drafts/%2F"):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 401 and r.json() == {"error": "errors.authRequired"}
        assert r.headers["cache-control"] == "private, no-store"
    app.dependency_overrides[current_owner] = lambda: {"id": OWNER}
    for path in ("/api/drafts/a%2Fb", "/api/drafts/%2F"):
        for method in ("GET", "PUT"):
            r = client.request(method, path, content="[", follow_redirects=False)
            assert r.status_code == 404 and r.json() == {"error": "errors.draftNotFound"}
            if method == "GET":
                assert r.headers["cache-control"] == "private, no-store"


def test_deep_json_is_invalid_body_not_generic_server_error():
    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[current_owner] = lambda: {"id": OWNER}
    r = TestClient(app).post(
        "/api/drafts", content='{"ignored":' + "[" * 20000 + "0" + "]" * 20000 + "}"
    )
    assert r.status_code == 400 and r.json() == {"error": "errors.requestBodyInvalid"}


def test_openapi_editor_optionals_are_omittable_but_not_nullable():
    paths = create_app(Settings(_env_file=None)).openapi()["paths"]
    schema = paths["/api/drafts"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    editor = schema["properties"]["draftDocument"]["properties"]["changeOrder"]["anyOf"][0]
    for key in ("reference", "changeOrderLabels", "aiValues"):
        assert key not in editor["required"]
        assert '"type": "null"' not in json.dumps(editor["properties"][key])
    assert "headers" in paths["/api/drafts"]["get"]["responses"]["200"]


def test_draft_auth_errors_and_every_read_response_are_private():
    client = TestClient(create_app(Settings(_env_file=None)))
    for method, path in (
        ("GET", "/api/drafts"),
        ("GET", "/api/drafts/not-a-uuid"),
        ("POST", "/api/drafts"),
        ("PUT", "/api/drafts/not-a-uuid"),
    ):
        response = client.request(method, path, json={})
        assert response.status_code == 401
        assert response.json() == {"error": "errors.authRequired"}
        if method == "GET":
            assert response.headers["cache-control"] == "private, no-store"
