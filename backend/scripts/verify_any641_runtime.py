"""Real gateway/image acceptance with exclusively owned disposable infrastructure."""

import argparse
import copy
import json
import os
import socket
import subprocess
import tempfile
import time
from contextlib import ExitStack, contextmanager
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import httpx
from pypdf import PdfReader
from verify_any640 import DisposablePostgres, auth_server

from scope_guard.infrastructure.auth.draft_proofs import DraftProofs
from scope_guard.modules.analysis.domain import DraftProofBinding, DraftProofClaims, freeze
from scope_guard.modules.analysis.normalization import parse_snapshot

ROOT = Path(__file__).parents[2]
SECRET = "any641-synthetic-secret-at-least-32-characters"


def docker(*args):
    return subprocess.run(
        ["docker", *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@contextmanager
def image_service(image, network, name, environment, port):
    token = uuid4().hex
    args = [
        "run",
        "--rm",
        "-d",
        "--network",
        network,
        "--name",
        name,
        "--label",
        "scope-guard.disposable=" + token,
        "-p",
        f"127.0.0.1::{port}",
    ]
    for key, value in environment.items():
        args += ["-e", key + "=" + value]
    identifier = docker(*args, image)
    try:
        published = docker("port", identifier, f"{port}/tcp").rsplit(":", 1)[1]
        yield "http://127.0.0.1:" + published
    finally:
        assert (
            docker(
                "inspect",
                "--format",
                '{{index .Config.Labels "scope-guard.disposable"}}',
                identifier,
            )
            == token
        )
        docker("rm", "-f", identifier)


@contextmanager
def next_server(environment):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(
            [
                "node",
                "node_modules/next/dist/bin/next",
                "start",
                "--hostname",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=ROOT / "frontend",
            env=environment,
            stdout=log,
            stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            yield f"http://127.0.0.1:{port}"
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def wait_ready(client, origin, path):
    for _ in range(120):
        try:
            if client.get(origin + path).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    raise RuntimeError("owned_service_readiness_failed")


def journey(client, origin):
    fixture = json.loads(
        (ROOT / "backend/tests/fixtures/contracts.json").read_text(encoding="utf-8")
    )
    checks = 0

    def request(method, path, **kwargs):
        return client.request(method, origin + path, **kwargs)

    for path in ("/api/scope/extract", "/api/change-orders/pdf"):
        response = request("POST", path)
        assert (
            response.status_code == 401 and response.headers["cache-control"] == "private, no-store"
        )
        checks += 1
    response = request(
        "POST", "/api/auth/register", json={"email": "owner@any641.test", "password": "12345678"}
    )
    assert response.status_code == 201
    owner = response.json()["user"]["id"]
    card = {
        "name": "Historical Website",
        "industry": "Development",
        "scope": "Five pages",
        "startDate": "2026-01-01",
        "pricingModel": "hourly",
        "currency": "EUR",
        "hourlyRate": "100",
    }
    response = request("POST", "/api/projects", json=card)
    assert response.status_code == 201
    project = response.json()["project"]["id"]
    document = copy.deepcopy(fixture["document"])
    document["changeOrder"].update(
        description="Edited commercial value — Español / Русский", additionalCost="2.675"
    )
    preview = {"projectId": project, "changeOrder": document["changeOrder"]}

    def assert_pdf(response, amount):
        assert response.status_code == 200, response.status_code
        assert response.headers["content-type"] == "application/pdf"
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["content-disposition"].startswith(
            'attachment; filename="change-order-'
        )
        content = " ".join(
            page.extract_text() for page in PdfReader(BytesIO(response.content)).pages
        )
        assert amount + " EUR" in content and "Español" in content and "Русский" in content

    assert_pdf(request("POST", "/api/change-orders/pdf", json=preview), "2.675")
    checks += 1
    claims = DraftProofClaims(
        DraftProofBinding(owner, project, "Extra page", "en"),
        parse_snapshot(fixture["analysis"], "en"),
        freeze(fixture["snapshot"]),
    )
    response = request(
        "POST",
        "/api/drafts",
        json={
            "projectId": project,
            "request": "Extra page",
            "locale": "en",
            "idempotencyKey": str(uuid4()),
            "proof": DraftProofs(SECRET, time.time).issue(claims),
            "draftDocument": document,
        },
    )
    assert response.status_code == 201, (response.status_code, response.json())
    draft = response.json()["draft"]
    path = f"/api/drafts/{draft['id']}"
    before = request("GET", path).json()
    for _ in range(2):
        assert_pdf(request("GET", path + "/pdf"), "2.675")
        checks += 1
    assert request("GET", path).json() == before
    checks += 1
    response = request(
        "POST",
        "/api/scope/extract",
        files={"file": ("scope.md", "Editable scope\r\nРусский".encode(), "text/markdown")},
    )
    assert response.status_code == 200 and response.json() == {
        "text": "Editable scope\nРусский",
        "warnings": [],
    }
    checks += 1
    pdf = request("GET", path + "/pdf").content
    response = request(
        "POST", "/api/scope/extract", files={"file": ("scope.pdf", pdf, "application/pdf")}
    )
    assert response.status_code == 200 and "Español" in response.json()["text"]
    checks += 1
    response = request(
        "POST",
        "/api/scope/extract",
        files={"file": ("scope.txt", b"x" * (5 * 1024 * 1024 + 1), "text/plain")},
    )
    assert response.status_code == 413
    checks += 1
    response = request(
        "POST",
        "/api/scope/extract",
        files={"file": ("scope.txt", b"Scope", "text/plain")},
        headers={"Origin": "https://foreign.test"},
    )
    assert response.status_code == 403 and response.headers["cache-control"] == "private, no-store"
    checks += 1
    client.cookies.clear()
    assert request("GET", path + "/pdf").status_code == 401
    checks += 1
    return checks


def main():
    from verify_any640 import prepare_alembic

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--containers", action="store_true")
    parser.add_argument("--backend-image", default="scg-any641-backend-check")
    parser.add_argument("--frontend-image", default="scg-any641-frontend-check")
    arguments = parser.parse_args()
    with DisposablePostgres() as postgres, postgres.database() as url, ExitStack() as stack:
        prepare_alembic(url)
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("SCOPE_GUARD_", "SCG_", "PG"))
            and key not in ("DATABASE_URL", "AUTH_SECRET", "OPENAI_API_KEY")
        }
        env.update(
            SCG_AUTH_REALTIME="1",
            SCOPE_GUARD_DATABASE_URL=url,
            SCOPE_GUARD_AUTH_SECRET=SECRET,
            AUTH_SECRET=SECRET,
            SCOPE_GUARD_PRODUCTION="false",
            NEXT_TELEMETRY_DISABLED="1",
        )
        if arguments.containers:
            network = "scg-any641-" + uuid4().hex
            docker("network", "create", network)
            stack.callback(docker, "network", "rm", network)
            docker("network", "connect", network, postgres.container_id)
            stack.callback(docker, "network", "disconnect", network, postgres.container_id)
            parsed = urlsplit(url)
            env["SCOPE_GUARD_DATABASE_URL"] = urlunsplit(
                parsed._replace(netloc=f"{parsed.username}:{parsed.password}@{postgres.name}:5432")
            )
            backend_name = "scg-any641-backend-" + uuid4().hex
            backend = stack.enter_context(
                image_service(
                    arguments.backend_image,
                    network,
                    backend_name,
                    {key: value for key, value in env.items() if key.startswith("SCOPE_GUARD_")},
                    8000,
                )
            )
            origin = stack.enter_context(
                image_service(
                    arguments.frontend_image,
                    network,
                    "scg-any641-frontend-" + uuid4().hex,
                    {
                        "AUTH_SECRET": SECRET,
                        "SCOPE_GUARD_API_ORIGIN": f"http://{backend_name}:8000",
                        "NEXT_TELEMETRY_DISABLED": "1",
                    },
                    3000,
                )
            )
        else:
            backend = stack.enter_context(auth_server(env))
            env["SCOPE_GUARD_API_ORIGIN"] = backend
            origin = stack.enter_context(next_server(env))
        with httpx.Client(trust_env=False, timeout=45) as client:
            wait_ready(client, backend, "/health/live")
            wait_ready(client, origin, "/login")
            result = journey(client, origin)
        print(
            json.dumps(
                {
                    "mode": "containers" if arguments.containers else "production-gateway",
                    "checks": result,
                    "disposableOnly": True,
                }
            )
        )


if __name__ == "__main__":
    main()
