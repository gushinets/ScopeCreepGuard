"""Exercise the actual static image against an owned deterministic HTTP upstream."""

import argparse
import json
import os
import socket
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from verify_any641_runtime import docker


@contextmanager
def static_image(image, upstream):
    token = uuid4().hex
    identifier = docker(
        "run",
        "--rm",
        "-d",
        "--label",
        "scope-guard.disposable=" + token,
        "-e",
        "SCOPE_GUARD_API_ORIGIN=" + upstream,
        *([] if os.name == "nt" else ["--add-host", "host.docker.internal:host-gateway"]),
        "-p",
        "127.0.0.1::3000",
        image,
    )
    try:
        port = docker("port", identifier, "3000/tcp").rsplit(":", 1)[1]
        origin = "http://127.0.0.1:" + port
        with httpx.Client(trust_env=False) as client:
            for _ in range(100):
                try:
                    if client.get(origin + "/health/live").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.1)
            else:
                raise RuntimeError("Static image failed startup: " + docker("logs", identifier))
        yield origin, identifier
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="scope-guard-react-migration:check")
    args = parser.parse_args()
    calls = []
    cancel_started = threading.Event()
    cancelled = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            self.do_POST()

        def do_PUT(self):
            self.do_POST()

        def do_PATCH(self):
            self.do_POST()

        def do_DELETE(self):
            self.do_POST()

        def do_POST(self):
            if self.path == "/api/cancel":
                cancel_started.set()
                self.connection.settimeout(5)
                try:
                    if self.connection.recv(1) == b"":
                        cancelled.set()
                except ConnectionResetError:
                    cancelled.set()
                return
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if self.headers.get("Transfer-Encoding") == "chunked":
                parts = []
                while size := int(self.rfile.readline().strip(), 16):
                    parts.append(self.rfile.read(size))
                    self.rfile.read(2)
                self.rfile.readline()
                body = b"".join(parts)
            calls.append((self.command, self.path, dict(self.headers), body))
            if self.path.startswith("/api/disconnect"):
                self.connection.close()
                return
            status = (
                429
                if self.path.startswith("/api/rate")
                else 307
                if self.path.startswith("/api/redirect")
                else 200
            )
            self.send_response(status)
            self.send_header(
                "Content-Type",
                "application/pdf" if self.path.startswith("/api/pdf") else "application/json",
            )
            self.send_header("Content-Disposition", 'attachment; filename="change-order-test.pdf"')
            self.send_header("Set-Cookie", "scg_session=synthetic; Path=/; HttpOnly; SameSite=lax")
            self.send_header("Set-Cookie", "scg_browser=browser; Path=/; HttpOnly; SameSite=lax")
            self.send_header("Retry-After", "30")
            self.send_header("X-Request-ID", self.headers.get("X-Request-ID", "upstream"))
            if status == 307:
                self.send_header("Location", "https://external.invalid/")
            self.end_headers()
            self.wfile.write(
                b"%PDF-\x00\xff"
                if self.path.startswith("/api/pdf")
                else b'{"error":"errors.requestFailed"}'
            )

    server = ThreadingHTTPServer(("0.0.0.0", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    checks = 0
    try:
        with static_image(args.image, "http://host.docker.internal:" + str(server.server_port)) as (
            origin,
            identifier,
        ):
            with httpx.Client(base_url=origin, trust_env=False, follow_redirects=False) as client:
                for path in [
                    "/",
                    "/login",
                    "/forgot-password",
                    "/reset-password",
                    "/projects/new",
                    "/projects/id/edit?draft=old",
                    "/history",
                    "/drafts",
                ]:
                    response = client.get(path)
                    assert response.status_code == 200 and '<div id="root">' in response.text
                    assert response.headers["cache-control"] == "no-store"
                    assert response.headers["referrer-policy"] == "no-referrer"
                    checks += 1
                assert client.get("/assets/missing.js").status_code == 404
                checks += 1
                for method, path in [
                    ("GET", "/api"),
                    ("GET", "/api/unknown"),
                    ("POST", "/api/v2/projects?keep=yes"),
                    ("PUT", "/api/v2/drafts/id"),
                    ("PATCH", "/api/projects/id"),
                    ("DELETE", "/api/projects/id"),
                ]:
                    response = client.request(
                        method,
                        path,
                        content=b"raw \xf0\x9f\x98\x80",
                        headers={
                            "Cookie": "scg_session=owner; locale=ru",
                            "Origin": "https://app.test",
                            "Content-Type": "application/json",
                            "X-Request-ID": "correlation",
                            "Idempotency-Key": "same-key",
                            "Authorization": "ignored",
                            "X-Forwarded-Host": "evil.test",
                        },
                    )
                    sent_method, sent_path, headers, body = calls[-1]
                    assert (sent_method, sent_path, body) == (
                        method,
                        path,
                        b"raw \xf0\x9f\x98\x80",
                    ), (method, path, response.status_code, calls[-1], docker("logs", identifier))
                    assert (
                        headers["Cookie"] == "scg_session=owner; locale=ru"
                        and headers["Origin"] == "https://app.test"
                    )
                    assert (
                        headers["Idempotency-Key"] == "same-key"
                        and "Authorization" not in headers
                        and "X-Forwarded-Host" not in headers
                    )
                    assert len(response.headers.get_list("set-cookie")) == 2
                    assert (
                        response.headers["x-request-id"] == "correlation"
                        and response.headers["cache-control"] == "private, no-store"
                    )
                    checks += 1
                response = client.get("/api/pdf")
                assert response.content == b"%PDF-\x00\xff" and response.headers[
                    "content-disposition"
                ].endswith('"change-order-test.pdf"')
                checks += 1
                before = len(calls)
                response = client.post("/api/rate", json={})
                assert (
                    response.status_code == 429
                    and response.headers["retry-after"] == "30"
                    and len(calls) == before + 1
                )
                checks += 1
                response = client.get("/api/redirect")
                assert (
                    response.status_code == 307
                    and response.headers["location"] == "https://external.invalid/"
                )
                checks += 1
                before = len(calls)
                response = client.post("/api/disconnect", json={})
                assert (
                    response.status_code == 503
                    and response.json() == {"error": "errors.requestFailed"}
                    and len(calls) == before + 1
                )
                checks += 1
                config = json.loads(docker("inspect", identifier))[0]["Config"]
                assert config["User"] != "root" and not any(
                    value.startswith("AUTH_SECRET=") for value in config["Env"]
                )
                checks += 1
                assert docker("exec", identifier, "sh", "-c", "command -v node || true") == ""
                checks += 1
                address = urlsplit(origin)
                downstream = socket.create_connection((address.hostname, address.port), timeout=5)
                downstream.sendall(b"GET /api/cancel HTTP/1.1\r\nHost: app.test\r\n\r\n")
                assert cancel_started.wait(5)
                downstream.shutdown(socket.SHUT_RDWR)
                downstream.close()
                assert cancelled.wait(5), "Client cancellation did not close the upstream request"
                checks += 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    print(
        json.dumps({"proxyChecks": checks, "realStaticImage": args.image, "disposableOnly": True})
    )


if __name__ == "__main__":
    main()
