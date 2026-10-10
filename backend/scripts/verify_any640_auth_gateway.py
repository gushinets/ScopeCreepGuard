"""Production Next.js -> FastAPI -> disposable PostgreSQL authentication journey."""

import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import psycopg
from verify_any640 import ROOT, DisposablePostgres, auth_server, replay_drizzle


def main(generation=False, drafts=False):
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
                # The shared session authorizes the Python-owned project API.
                status, _, projects = request("/api/projects", cookie=cookie)
                assert status == 200 and json.loads(projects) == {"projects": []}
                card = {
                    "name": "Gateway project",
                    "clientName": "Client",
                    "scope": "Five pages",
                    "industry": "Development",
                    "startDate": "2026-10-10",
                    "pricingModel": "hourly",
                    "currency": "EUR",
                    "hourlyRate": "100.20",
                }
                status, _, created = request("/api/projects", "POST", card, cookie)
                assert status == 201
                project = json.loads(created)["project"]
                path = "/api/projects/" + project["id"]
                assert request(path, cookie=cookie)[0] == 200
                assert len(json.loads(request("/api/projects", cookie=cookie)[2])["projects"]) == 1
                edited = {**card, "name": "Edited", "pricingModel": "fixed", "fixedPrice": "50"}
                del edited["clientName"]
                status, _, result = request(path, "PATCH", edited, cookie)
                assert status == 200 and json.loads(result)["project"]["clientName"] == "Client"
                assert json.loads(result)["project"]["hourlyRate"] is None
                status, _, result = request(path, "PATCH", {**edited, "clientName": None}, cookie)
                assert status == 200 and json.loads(result)["project"]["clientName"] is None
                assert request(path, "PATCH", {}, cookie)[0] == 400
                status, foreign_headers, _ = request(
                    "/api/auth/register", "POST", {**body, "email": "other@example.test"}
                )
                assert status == 201
                foreign_cookie = foreign_headers["set-cookie"].split(";")[0]
                for method in ("GET", "PATCH", "DELETE"):
                    assert (
                        request(path, method, {} if method == "PATCH" else None, foreign_cookie)[0]
                        == 404
                    )
                assert json.loads(request("/api/projects", cookie=foreign_cookie)[2]) == {
                    "projects": []
                }
                assert request("/api/projects", "POST", card, cookie, foreign=True)[0] == 403
                if generation or drafts:
                    generation_journey(
                        request, cookie + "; locale=en", foreign_cookie, project, url, backend
                    )
                assert request(path, "DELETE", cookie=cookie)[0] == 200
                assert request(path, cookie=cookie)[0] == 404
                assert json.loads(request("/api/projects", cookie=cookie)[2]) == {"projects": []}
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
                    "Gateway journeys: 15 auth and 14 project checks passed; "
                    "owned resources removed"
                )
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    return 0


def generation_journey(request, cookie, foreign_cookie, project, url, backend):
    fixture = json.loads(
        (ROOT / "contracts/compatibility/any-640/generation.json").read_text(encoding="utf-8")
    )
    body = {"projectId": project["id"], "request": "Add another page", "documentLanguage": "en"}

    def calls():
        with urllib.request.urlopen(backend + "/__generation_calls") as response:
            return json.load(response)["calls"]

    initial_calls = calls()
    status, headers, raw = request("/api/analyze", "POST", body, cookie)
    assert status == 200 and headers["cache-control"] == "private, no-store"
    assert headers["x-request-id"]
    analyzed = json.loads(raw)
    context = {
        "projectId": project["id"],
        "request": body["request"],
        "locale": "en",
        "proof": analyzed["proof"],
    }
    operations = (
        ("/api/replies/regenerate", {**body, "tone": "firm", "previousReply": "old"}),
        (
            "/api/client-materials/language",
            {**context, "clientLanguage": "en", "analysis": analyzed["result"]},
        ),
        ("/api/change-orders/estimate", context),
    )
    for path, payload in operations:
        status, response_headers, _ = request(path, "POST", payload, cookie)
        assert status == 200 and "cache-control" not in response_headers
        assert request(path, "POST", payload, foreign_cookie)[0] == 404
    with psycopg.connect(url) as database:
        assert database.execute("SELECT count(*) FROM drafts").fetchone()[0] == 0
        assert database.execute("SELECT count(*) FROM history_entries").fetchone()[0] == 0
        assert (
            database.execute(
                "SELECT last_checked FROM projects WHERE id=%s", (project["id"],)
            ).fetchone()[0]
            is None
        )
    assert calls() == initial_calls + 4
    document = {**fixture["documentFixture"], "result": analyzed["result"]}
    save = {
        **context,
        "idempotencyKey": "10000000-0000-4000-8000-000000000004",
        "draftDocument": document,
    }
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(lambda _: request("/api/drafts", "POST", save, cookie), range(2))
        )
    assert sorted(response[0] for response in responses) == [200, 201]
    drafts = [json.loads(response[2])["draft"] for response in responses]
    assert drafts[0]["id"] == drafts[1]["id"]
    reopened = json.loads(request("/api/drafts/" + drafts[0]["id"], cookie=cookie)[2])["draft"]
    assert reopened["analysisSnapshot"] == analyzed["result"]
    assert reopened["projectSnapshot"] == analyzed["projectSnapshot"]
    path = "/api/drafts/" + drafts[0]["id"]
    status, headers, raw = request("/api/drafts", cookie=cookie)
    assert status == 200 and headers["cache-control"] == "private, no-store"
    assert json.loads(raw)["drafts"][0]["id"] == drafts[0]["id"]
    changed = {**document, "reply": {**document["reply"], "text": "Editable gateway reply"}}
    status, _, raw = request("/api/drafts", "POST", {**save, "draftDocument": changed}, cookie)
    assert status == 200 and json.loads(raw)["draft"]["draftDocument"] == document
    status, _, raw = request(path, "PUT", {"draftDocument": changed}, cookie)
    assert status == 200
    updated = json.loads(raw)["draft"]
    assert updated["draftDocument"] == changed
    for field in ("analysisSnapshot", "projectSnapshot", "createdAt", "historyEntryId", "request"):
        assert updated[field] == reopened[field]
    for identifier in (drafts[0]["id"], "malformed", "10000000-0000-4000-8000-000000000009"):
        for method in ("GET", "PUT"):
            status, headers, raw = request(
                "/api/drafts/" + identifier, method, {} if method == "PUT" else None, foreign_cookie
            )
            assert status == 404 and json.loads(raw) == {"error": "errors.draftNotFound"}
            if method == "GET":
                assert headers["cache-control"] == "private, no-store"
    assert json.loads(request("/api/drafts", cookie=foreign_cookie)[2]) == {"drafts": []}
    assert calls() == initial_calls + 4
    with psycopg.connect(url) as database:
        assert database.execute("SELECT count(*) FROM drafts").fetchone()[0] == 1
        assert database.execute("SELECT count(*) FROM history_entries").fetchone()[0] == 1
        database.execute(
            "UPDATE projects SET scope='Current scope', hourly_rate=NULL, "
            "fixed_price=999 WHERE id=%s",
            (project["id"],),
        )
    for path, payload in operations[1:]:
        assert request(path, "POST", {**payload, "draftId": drafts[0]["id"]}, cookie)[0] == 200
    for _ in range(4):
        assert request("/api/replies/regenerate", "POST", operations[0][1], cookie)[0] == 200
    status, _, raw = request("/api/analyze", "POST", body, cookie)
    assert status == 429 and json.loads(raw) == {"error": "errors.analysisRateLimited"}
    assert calls() == initial_calls + 10
    print(
        "Generation gateway: four owners, zero generation writes, "
        "Python proof -> Python drafts/list/PUT/reload/dedup, owner isolation, "
        "historical context and shared limit passed."
    )


if __name__ == "__main__":
    raise SystemExit(main())
