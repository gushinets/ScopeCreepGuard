"""Build and HTTP-smoke owned containers; never attach an application database."""

import json
import subprocess
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_DB = "postgres://scg_test:synthetic@127.0.0.1:9/scg_test_build"


def docker(*args):
    return subprocess.run(
        ["docker", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


@contextmanager
def container(image, port, environment):
    owner = uuid4().hex
    arguments = [
        "run",
        "--rm",
        "-d",
        "--label",
        "scope-guard.disposable=" + owner,
        "-p",
        f"127.0.0.1::{port}",
    ]
    for key, value in environment.items():
        arguments += ["-e", f"{key}={value}"]
    identifier = docker(*arguments, image)
    try:
        published = docker("port", identifier, f"{port}/tcp").rsplit(":", 1)[1]
        yield "http://127.0.0.1:" + published
    finally:
        label = docker(
            "inspect", "--format", '{{index .Config.Labels "scope-guard.disposable"}}', identifier
        )
        if label != owner:
            raise RuntimeError("container_ownership_changed")
        docker("rm", "-f", identifier)


def request(url, method="GET", body=None, origin=None):
    headers = {"content-type": "application/json"}
    if origin is not None:
        headers["origin"] = origin
    req = urllib.request.Request(
        url,
        method=method,
        headers=headers,
        data=None if body is None else json.dumps(body).encode(),
    )
    # Do not use inherited proxy settings for loopback verification.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        response = opener.open(req, timeout=3)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, response.headers, response.read().decode()


def wait_ready(url):
    for _ in range(40):
        try:
            assert request(url)[0] == 200
            return
        except (OSError, AssertionError):
            time.sleep(0.25)
    raise RuntimeError("container_readiness_failed")


def main():
    for name, args in (
        ("backend", ["backend"]),
        (
            "frontend",
            ["--target", "runner", "--build-arg", "DATABASE_URL=" + SYNTHETIC_DB, "frontend"],
        ),
    ):
        subprocess.run(
            ["docker", "build", "-t", f"scg-any640-{name}-check", *args], cwd=ROOT, check=True
        )
    allowed = '["https://app.test"]'
    with container(
        "scg-any640-backend-check", 8000, {"SCOPE_GUARD_ALLOWED_ORIGINS": allowed}
    ) as backend:
        wait_ready(backend + "/health/live")
        assert json.loads(request(backend + "/health/live")[2]) == {"status": "ok"}
        status, _, body = request(backend + "/api/locale", "POST", {}, "https://evil.test")
        assert status == 403 and json.loads(body) == {"error": "errors.requestFailed"}
    with container(
        "scg-any640-frontend-check",
        3000,
        {
            "DATABASE_URL": SYNTHETIC_DB,
            "AUTH_SECRET": "synthetic-container-secret-32-characters",
            "SCOPE_GUARD_ALLOWED_ORIGINS": allowed,
            "OPENAI_API_KEY": "",
        },
    ) as frontend:
        wait_ready(frontend + "/login")
        for path in ("/api/locale", "/api/auth/register", "/api/analyze"):
            status, _, body = request(frontend + path, "POST", {}, "https://evil.test")
            assert status == 403 and json.loads(body) == {"error": "errors.requestFailed"}
        status, headers, body = request(
            frontend + "/api/locale", "POST", {"locale": "ru"}, "https://app.test"
        )
        assert status == 200 and json.loads(body) == {"ok": True}
        assert "locale=ru" in headers["set-cookie"] and "HttpOnly" not in headers["set-cookie"]
        status, _, body = request(frontend + "/api/analyze", "POST", {}, "https://app.test")
        assert status == 401 and json.loads(body) == {"error": "errors.authRequired"}
        assert request(frontend + "/api/locale", "POST", {"locale": "en"})[0] == 200
    print("Container builds and production HTTP smoke: 8 checks passed; owned containers removed.")
    print("Independent deployment smoke passed; full browser workflows remain a later-slice gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
