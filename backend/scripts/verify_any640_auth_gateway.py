"""Production Next.js -> FastAPI -> disposable PostgreSQL authentication journey."""

import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

import psycopg
from verify_any640 import ROOT, DisposablePostgres, auth_server, replay_drizzle


def main():
    with DisposablePostgres() as server, server.database() as url:
        replay_drizzle(url)
        env = dict(os.environ)
        env.update(
            DATABASE_URL=url,
            SCOPE_GUARD_DATABASE_URL=url,
            AUTH_SECRET="any640-synthetic-contract-secret-at-least-32-characters",
            SCOPE_GUARD_PRODUCTION="true",
            OPENAI_API_KEY="",
            NEXT_TELEMETRY_DISABLED="1",
            SCG_AUTH_REALTIME="1",
        )
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        origin = f"http://127.0.0.1:{port}"
        env.update(SCOPE_GUARD_ALLOWED_ORIGINS=json.dumps([origin]))
        # Keep Python alive for the whole frontend journey.
        with auth_server(env) as backend, tempfile.TemporaryFile() as log:
            env["SCOPE_GUARD_API_ORIGIN"] = backend
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
                env=env,
                stdout=log,
                stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *args, **kwargs):
                    return None

            client = urllib.request.build_opener(NoRedirect)

            def request(path, method="GET", body=None, cookie=None, foreign=False):
                headers = {"content-type": "application/json"}
                if cookie:
                    headers["cookie"] = cookie
                if foreign:
                    headers["origin"] = "https://foreign.test"
                req = urllib.request.Request(
                    origin + path,
                    data=json.dumps(body).encode() if body is not None else None,
                    headers=headers,
                    method=method,
                )
                try:
                    response = client.open(req, timeout=10)
                except urllib.error.HTTPError as error:
                    response = error
                with response:
                    return response.status, response.headers, response.read()

            try:
                for _ in range(200):
                    if process.poll() is not None:
                        raise RuntimeError("Owned Next.js server failed to start")
                    try:
                        if request("/api/auth/me")[0] == 401:
                            break
                    except OSError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Owned Next.js startup timed out")
                body = {"email": " Owner@Example.Test ", "password": "synthetic-password"}
                status, headers, result = request("/api/auth/register", "POST", body)
                assert status == 201
                user = json.loads(result)["user"]
                assert user["email"] == "owner@example.test"
                cookie = headers["set-cookie"].split(";")[0]
                assert all(
                    flag in headers["set-cookie"]
                    for flag in ("Secure", "HttpOnly", "SameSite=lax", "Max-Age=604800")
                )
                assert request("/api/auth/register", "POST", body)[0] == 409
                assert json.loads(request("/api/auth/me", cookie=cookie)[2])["user"] == user
                assert request("/login", cookie=cookie)[0] == 307
                assert (
                    request("/api/auth/login", "POST", {**body, "password": "wrong-password"})[0]
                    == 401
                )
                assert request("/api/auth/login", "POST", body)[0] == 200
                assert request("/api/auth/register", "POST", body, foreign=True)[0] == 403
                # Python-issued sessions authorize still-TypeScript business routes.
                status, _, projects = request("/api/projects", cookie=cookie)
                assert status == 200 and json.loads(projects) == {"projects": []}
                status, headers, _ = request("/api/auth/logout", "POST", cookie=cookie)
                assert status == 200 and "Max-Age=0" in headers["set-cookie"]
                assert request("/api/auth/me", cookie="scg_session=malformed")[0] == 401
                with psycopg.connect(url) as database:
                    database.execute("DELETE FROM users")
                status, headers, _ = request("/login", cookie=cookie)
                assert status == 200 and "location" not in headers
                assert "Max-Age=0" in headers["set-cookie"]
                assert request("/api/auth/me", cookie=cookie)[0] == 401
                assert request("/api/projects", cookie=cookie)[0] == 401
                print(
                    "Auth gateway journey: 15 checks passed; owned database and processes removed"
                )
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
