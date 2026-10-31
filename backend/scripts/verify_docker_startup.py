"""Verify documented Compose topology and lifecycle using disposable Docker resources."""

import argparse
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import yaml

ROOT = Path(__file__).resolve().parents[2]
APPLICATION_STACK = {
    "postgres",
    "migrate",
    "backend",
    "app",
    "llm-worker",
    "export-worker",
    "email-worker",
}
SERVICES = APPLICATION_STACK | {"mailpit"}
CLOSURES = {
    "postgres": {"postgres"},
    "backend": {"postgres", "migrate", "backend"},
    "frontend": {"postgres", "migrate", "backend", "app"},
    "llm-worker": {"postgres", "migrate", "llm-worker"},
    "export-worker": {"postgres", "migrate", "export-worker"},
    "email-worker": {"postgres", "migrate", "email-worker"},
}


def wait_for_confirmation(
    mailpit,
    recipient,
    public_origin,
    owner_id,
    *,
    timeout=15,
    clock=time.monotonic,
    sleep=time.sleep,
):
    """Test-only bounded capture polling; never print the returned raw token."""
    deadline = clock() + timeout
    while clock() < deadline:
        response = mailpit.get("/api/v1/messages", timeout=min(2, deadline - clock()))
        response.raise_for_status()
        for item in response.json()["messages"]:
            if not any(address["Address"] == recipient for address in item["To"]):
                continue
            remaining = deadline - clock()
            if remaining <= 0:
                break
            response = mailpit.get("/api/v1/message/" + item["ID"], timeout=min(2, remaining))
            response.raise_for_status()
            try:
                links = [
                    line.strip()
                    for line in response.json()["Text"].splitlines()
                    if line.strip().startswith(("http://", "https://"))
                ]
                if len(links) != 1:
                    raise ValueError
                url = urlsplit(links[0])
                fields = parse_qs(url.fragment, strict_parsing=True)
                if (
                    f"{url.scheme}://{url.netloc}" != public_origin
                    or url.path != "/confirm-email"
                    or url.query
                    or set(fields) != {"userId", "token"}
                    or fields["userId"] != [owner_id]
                    or len(fields["token"]) != 1
                    or not 20 <= len(fields["token"][0]) <= 128
                ):
                    raise ValueError
                return {"userId": owner_id, "token": fields["token"][0]}
            except (KeyError, TypeError, ValueError):
                raise AssertionError("Invalid confirmation email link") from None
        sleep(min(0.2, max(0, deadline - clock())))
    raise AssertionError("Confirmation email did not arrive before the polling deadline")


def copy_deployment_fixture(source, destination):
    """Copy maintained definitions/helpers only, never developer .env files or reports."""
    bootstrap = source / "deploy/.env"
    settings = [
        line
        for line in bootstrap.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert settings == ["COMPOSE_FILE=../compose.yaml"]
    paths = [
        source / "compose.yaml",
        bootstrap,
        *list((source / "deploy").glob("*.yaml")),
        *list((source / "deploy").glob("*.yml")),
        *list((source / "deploy/compose").glob("*.yaml")),
        source / "deploy/silo/init.sh",
        source / "scripts/stack.py",
        source / "scripts/verify_mailpit.py",
        source / "backend/alembic/env.py",
    ]
    for path in paths:
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def verify(*, api_image, frontend_image, worker_image, config_only=False, compose_binary=None):
    root = ROOT
    executable = [str(Path(compose_binary).resolve())] if compose_binary else ["docker", "compose"]
    token = uuid4().hex
    project = "scg-startup-test-" + token
    # Choose the browser-reachable origin before starting the API so email links
    # use configured public state rather than Host/forwarded headers.
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        frontend_port = listener.getsockname()[1]
    public_origin = f"http://127.0.0.1:{frontend_port}"
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("SCOPE_GUARD_", "SCG_", "PG", "COMPOSE_"))
        and key not in {"DATABASE_URL", "AUTH_SECRET", "OPENAI_API_KEY", "OPENAI_MODEL"}
    }
    environment.update(
        AUTH_SECRET="synthetic-startup-secret-at-least-32-characters",
        OPENAI_API_KEY="synthetic-no-paid-jobs",
        SCOPE_GUARD_OPENAI_MODEL="gpt-6-luna",
        SCOPE_GUARD_LLM_INPUT_RATE_BOUND="0.000001",
        SCOPE_GUARD_LLM_OUTPUT_RATE_BOUND="0.000005",
        SCOPE_GUARD_EXPORT_BUCKET="startup-test",
        SCOPE_GUARD_EXPORT_ACCESS_KEY="synthetic",
        SCOPE_GUARD_EXPORT_SECRET_KEY="synthetic-storage-secret",
        SCOPE_GUARD_EXPORT_ENDPOINT="http://storage:9000",
        SCOPE_GUARD_API_IMAGE=api_image,
        SCOPE_GUARD_FRONTEND_IMAGE=frontend_image,
        SCOPE_GUARD_WORKER_IMAGE=worker_image,
        MAILPIT_UI_PORT="0",
        POSTGRES_PORT="0",
        BACKEND_PORT="0",
        FRONTEND_PORT=f"127.0.0.1:{frontend_port}",
        SCOPE_GUARD_PUBLIC_APP_URL=public_origin,
        SCOPE_GUARD_ALLOWED_ORIGINS=json.dumps([public_origin]),
        COMPOSE_DISABLE_ENV_FILE="1",
        HTTP_PROXY="",
        HTTPS_PROXY="",
        NO_PROXY="postgres,backend,storage,localhost,127.0.0.1",
    )
    results = []

    def run(*args, check=True, timeout=240):
        if compose_binary and args[:2] == ("docker", "compose"):
            args = (str(Path(compose_binary).resolve()), *args[2:])
        result = subprocess.run(
            list(args), cwd=root, env=environment, text=True, capture_output=True, timeout=timeout
        )
        if check and result.returncode:
            # Only synthetic configuration is loaded by this harness.
            raise AssertionError(
                f"Command failed ({result.returncode}): {' '.join(args)}\n"
                + result.stdout
                + result.stderr
            )
        return result

    with tempfile.TemporaryDirectory(prefix="scg-startup-") as directory:
        checkout = Path(directory) / "checkout"
        copy_deployment_fixture(root, checkout)
        root = checkout
        empty = Path(directory) / "empty.env"
        empty.write_text("")
        environment.update(
            {
                key: str(empty)
                for key in (
                    "SCOPE_GUARD_LOCAL_ENV_FILE",
                    "SCOPE_GUARD_LOCAL_OVERRIDE_ENV_FILE",
                    "SCOPE_GUARD_BACKEND_ENV_FILE",
                )
            }
        )

        def compose(*args, entry="compose.yaml", check=True):
            files = ["-f", str(root / "deploy" / entry)]
            # Temporary reference files must retain the repository as their path base.
            return run(
                "docker",
                "compose",
                "--project-directory",
                str(root if Path(entry) == root / "compose.yaml" else root / "deploy"),
                "--env-file",
                str(empty),
                "-p",
                project,
                *files,
                *args,
                check=check,
            )

        def config(entry):
            return json.loads(
                compose(
                    "config",
                    "--format",
                    "json",
                    entry=entry,
                ).stdout
            )

        compose_version = run("docker", "compose", "version", "--short").stdout.strip().lstrip("v")
        legacy_env_discovery = compose_version == "2.24.0"
        results.append("Compose " + compose_version)
        full = config("compose.yaml")
        assert set(full["services"]) == SERVICES
        assert Path(full["services"]["backend"]["build"]["context"]) == root
        assert Path(full["services"]["app"]["build"]["context"]) == root / "frontend"
        assert full["services"]["mailpit"]["ports"][0]["host_ip"] == "127.0.0.1"
        assert {port["target"] for port in full["services"]["mailpit"]["ports"]} == {8025}
        mailpit_environment = full["services"]["mailpit"]["environment"]
        assert not any(
            key.startswith(("MP_SMTP_RELAY", "MP_SMTP_FORWARD", "MP_SMTP_AUTH"))
            for key in mailpit_environment
        )
        assert mailpit_environment["MP_DATABASE"] == "/data/mailpit.db"
        assert str(mailpit_environment["MP_MAX_MESSAGES"]) == "500"
        assert mailpit_environment["MP_MAX_AGE"] == "7d"
        for role in ("llm-worker", "export-worker"):
            for key in (
                "SCOPE_GUARD_DATABASE_URL",
                "SCOPE_GUARD_PRODUCTION",
                "SCOPE_GUARD_LOG_LEVEL",
                "SCOPE_GUARD_WORKFLOW_V2",
                "SCOPE_GUARD_LLM_WORKFLOW",
            ):
                assert (
                    full["services"][role]["environment"][key]
                    == (full["services"]["backend"]["environment"][key])
                )
        assert full["volumes"]["scope_creep_guard_mailpit"]["name"] == (
            project + "_scope_creep_guard_mailpit"
        )
        assert not any(
            "mailpit" in full["services"][service].get("depends_on", {})
            for service in ("backend", "llm-worker", "export-worker")
        )
        for working_directory, filename in (
            (root, "deploy/compose.yaml"),
            (root / "deploy", "compose.yaml"),
        ):
            command = [
                *executable,
                "--env-file",
                str(empty),
                "-p",
                project,
                "-f",
                filename,
                "config",
                "--format",
                "json",
            ]
            result = subprocess.run(
                command,
                cwd=working_directory,
                env=environment,
                text=True,
                capture_output=True,
                check=True,
            )
            assert json.loads(result.stdout) == full
        for alias in (str(root / "compose.yaml"), "compose.services.yaml", "docker-compose.yml"):
            assert config(alias) == full

        # Prove bare root invocation loads .env, without touching developer secrets.
        fixture = Path(directory) / "automatic-env"
        copy_deployment_fixture(root, fixture)
        fixture_values = {
            key: value
            for key, value in environment.items()
            if key.startswith("SCOPE_GUARD_")
            or key
            in {
                "AUTH_SECRET",
                "OPENAI_API_KEY",
                "MAILPIT_UI_PORT",
                "POSTGRES_PORT",
                "BACKEND_PORT",
                "FRONTEND_PORT",
            }
        }
        fixture_values["COMPOSE_PROJECT_NAME"] = project
        (fixture / ".env").write_text(
            "\n".join(key + "=" + json.dumps(value) for key, value in fixture_values.items())
            + "\n",
            encoding="utf-8",
        )
        automatic_environment = {
            key: value
            for key, value in environment.items()
            if key not in fixture_values and key != "COMPOSE_DISABLE_ENV_FILE"
        }
        automatic = subprocess.run(
            [*executable, "config", "--format", "json"],
            cwd=fixture,
            env=automatic_environment,
            text=True,
            capture_output=True,
            check=True,
        )
        explicit = subprocess.run(
            [
                *executable,
                "--env-file",
                ".env",
                "-f",
                "deploy/compose.yaml",
                "config",
                "--format",
                "json",
            ],
            cwd=fixture,
            env=automatic_environment,
            text=True,
            capture_output=True,
            check=True,
        )
        automatic_config = json.loads(automatic.stdout)
        assert automatic_config == json.loads(explicit.stdout)
        from_deploy = subprocess.run(
            [*executable, "config", "--format", "json"],
            cwd=fixture / "deploy",
            env=automatic_environment,
            text=True,
            capture_output=True,
            check=False,
        )
        if legacy_env_discovery:
            # 2.24 loads only deploy/.env, even after COMPOSE_FILE changes the root.
            # Keep this regression visible; only the explicit env-file fallback is supported.
            assert from_deploy.returncode != 0
            assert "required variable" in from_deploy.stderr
            from_deploy = subprocess.run(
                [*executable, "--env-file", "../.env", "config", "--format", "json"],
                cwd=fixture / "deploy",
                env=automatic_environment,
                text=True,
                capture_output=True,
                check=True,
            )
        assert from_deploy.returncode == 0, from_deploy.stderr
        assert json.loads(from_deploy.stdout) == automatic_config
        assert automatic_config["name"] == project
        assert (
            automatic_config["services"]["backend"]["environment"]["AUTH_SECRET"]
            == (fixture_values["AUTH_SECRET"])
        )
        assert automatic_config["volumes"]["scope_creep_guard_postgres"]["name"] == (
            project + "_scope_creep_guard_postgres"
        )
        results.append(
            "root auto .env / deploy "
            + ("explicit .env" if legacy_env_discovery else "auto .env")
            + ": project identity and canonical parity"
        )
        mailpit = config("compose.mailpit.yaml")
        assert set(mailpit["services"]) == {"mailpit"}
        assert mailpit["services"]["mailpit"] == full["services"]["mailpit"]
        assert full["volumes"]["scope_creep_guard_postgres"]["name"] == (
            project + "_scope_creep_guard_postgres"
        )
        environment.update(
            SCOPE_GUARD_POSTGRES_VOLUME=project + "-existing-volume",
            SCOPE_GUARD_POSTGRES_VOLUME_EXTERNAL="true",
        )
        external_volume = config("compose.postgres.yaml")["volumes"]["scope_creep_guard_postgres"]
        assert external_volume["name"] == project + "-existing-volume"
        assert external_volume["external"] is True
        environment.pop("SCOPE_GUARD_POSTGRES_VOLUME")
        environment.pop("SCOPE_GUARD_POSTGRES_VOLUME_EXTERNAL")
        for component, expected in CLOSURES.items():
            selected = config(f"compose.{component}.yaml")
            assert set(selected["services"]) == expected
            for service in expected:
                assert selected["services"][service] == full["services"][service]
            assert all(
                full["volumes"][key] == value for key, value in selected.get("volumes", {}).items()
            )
            assert selected["networks"] == full["networks"]
        for service in ("backend", "llm-worker", "export-worker"):
            assert (
                full["services"][service]["depends_on"]["migrate"]["condition"]
                == "service_completed_successfully"
            )
        assert "backend" not in full["services"]["llm-worker"]["depends_on"]
        assert all(
            "SCOPE_GUARD_MIGRATION_TARGET" not in item.get("environment", {})
            for item in full["services"].values()
        )
        environment.update(
            POSTGRES_DB="scope_creep_guard",
            POSTGRES_USER="scopeguard",
            POSTGRES_PASSWORD="synthetic",
            DATABASE_URL="postgres://scopeguard:synthetic@postgres/scope_creep_guard",
            SCOPE_GUARD_ALLOWED_ORIGINS='["https://synthetic.example.test"]',
            SCOPE_GUARD_PUBLIC_APP_URL="https://synthetic.example.test",
            SCOPE_GUARD_SILO_ROOT_USER="synthetic-admin",
            SCOPE_GUARD_SILO_ROOT_PASSWORD="synthetic-admin-secret",
        )
        production = config("docker-compose.dokploy.yml")
        assert set(production["services"]) == APPLICATION_STACK | {"silo", "silo-init"}
        production_source = yaml.safe_load((root / "deploy/docker-compose.dokploy.yml").read_text())
        assert "app" in production_source.get("services", {}), (
            "Dokploy must see app before expanding Compose definitions"
        )
        reference_sources = production_source["include"]
        reference_sources.append({"path": ["compose/app.yaml", "compose/app.production.yaml"]})
        for source in reference_sources:
            paths = source["path"]
            source["path"] = (
                [str(root / "deploy" / path) for path in paths]
                if isinstance(paths, list)
                else str(root / "deploy" / paths)
            )
            source["project_directory"] = str(root)
        reference_path = Path(directory) / "production-reference.yaml"
        reference_path.write_text(yaml.safe_dump({"include": reference_sources}), encoding="utf-8")
        reference = config(str(reference_path))
        for section in ("services", "volumes", "networks"):
            assert production[section] == reference[section], section
        for service, definition in production["services"].items():
            assert not definition.get("ports")
            assert not definition.get("env_file")
            if service in SERVICES:
                expected_dependencies = dict(full["services"][service].get("depends_on", {}))
                if service in {"backend", "export-worker"}:
                    expected_dependencies["silo-init"] = {
                        "condition": "service_completed_successfully",
                        "required": True,
                    }
                assert definition.get("depends_on", {}) == expected_dependencies
        for key in (
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "DATABASE_URL",
            "SCOPE_GUARD_ALLOWED_ORIGINS",
            "SCOPE_GUARD_SILO_ROOT_USER",
            "SCOPE_GUARD_SILO_ROOT_PASSWORD",
        ):
            environment.pop(key)
        environment["SCOPE_GUARD_ALLOWED_ORIGINS"] = json.dumps([public_origin])
        environment["SCOPE_GUARD_PUBLIC_APP_URL"] = public_origin
        saved_secret = environment.pop("AUTH_SECRET")
        assert compose("config", "--quiet", check=False).returncode != 0
        assert compose("config", "--quiet", entry="compose.postgres.yaml").returncode == 0
        environment["AUTH_SECRET"] = saved_secret
        results.append(
            "configuration: root/deploy parity, entry points, paths, isolation, migration gates"
        )
        unrelated = {
            "llm-worker": (
                "AUTH_SECRET",
                "SCOPE_GUARD_EXPORT_BUCKET",
                "SCOPE_GUARD_EXPORT_ENDPOINT",
                "SCOPE_GUARD_EXPORT_REGION",
                "SCOPE_GUARD_EXPORT_ACCESS_KEY",
                "SCOPE_GUARD_EXPORT_SECRET_KEY",
            ),
            "export-worker": (
                "AUTH_SECRET",
                "OPENAI_API_KEY",
                "SCOPE_GUARD_OPENAI_MODEL",
                "SCOPE_GUARD_LLM_INPUT_RATE_BOUND",
                "SCOPE_GUARD_LLM_OUTPUT_RATE_BOUND",
                "SCOPE_GUARD_LLM_MAX_COST",
            ),
        }
        for component, keys in unrelated.items():
            saved = dict(environment)
            try:
                for key in keys:
                    environment.pop(key, None)
                selected = config(f"compose.{component}.yaml")
                assert set(selected["services"]) == CLOSURES[component]
                assert selected["services"]["postgres"] == full["services"]["postgres"]
                required = (
                    "OPENAI_API_KEY" if component == "llm-worker" else "SCOPE_GUARD_EXPORT_BUCKET"
                )
                environment.pop(required)
                assert (
                    compose(
                        "config", "--quiet", entry=f"compose.{component}.yaml", check=False
                    ).returncode
                    != 0
                )
            finally:
                environment.clear()
                environment.update(saved)
        results.append("worker configs require only their own role settings")
        if config_only:
            return results

        def sql(statement, database="scope_creep_guard"):
            return compose(
                "exec",
                "-T",
                "postgres",
                "psql",
                "-v",
                "ON_ERROR_STOP=1",
                "-U",
                "scopeguard",
                "-d",
                database,
                "-Atc",
                statement,
            ).stdout.strip()

        def logs(service="migrate"):
            return compose("logs", "--no-color", service).stdout

        def wait_log(identifier, marker):
            deadline = time.monotonic() + 60
            while (
                marker
                not in run("docker", "logs", identifier).stdout
                + run("docker", "logs", identifier).stderr
            ):
                assert time.monotonic() < deadline, f"Missing {marker}"
                time.sleep(0.2)

        def migrate_run(*args):
            return compose("run", "-d", "--no-deps", *args, "migrate").stdout.strip()

        def wait_exit(identifier, code="0"):
            assert run("docker", "wait", identifier, timeout=90).stdout.strip() == code
            return (
                run("docker", "logs", identifier).stdout + run("docker", "logs", identifier).stderr
            )

        storage = project + "-storage"
        fault_images = []
        try:
            # First use a component, establishing the same project volume/network.
            compose("up", "-d", "--no-build", "--wait", entry="compose.postgres.yaml")
            postgres_id = compose("ps", "-q", "postgres").stdout.strip()
            existing_environment = Path(directory) / "existing-project.env"
            existing_environment.write_text("COMPOSE_PROJECT_NAME=" + project + "\n")
            wrapper_status = run(
                os.sys.executable,
                str(root / "scripts/stack.py"),
                "status",
                "--env-file",
                str(existing_environment),
            )
            assert project + "-postgres-1" in wrapper_status.stdout
            results.append("wrapper honors existing project name from --env-file")
            mounts = run("docker", "inspect", "--format", "{{json .Mounts}}", postgres_id).stdout
            # External storage fixture, no production service or dependency changes.
            run(
                "docker",
                "run",
                "-d",
                "--name",
                storage,
                "--label",
                "scope-guard.disposable=" + token,
                "--network",
                project + "_default",
                "--network-alias",
                "storage",
                "-e",
                "MINIO_ROOT_USER=synthetic",
                "-e",
                "MINIO_ROOT_PASSWORD=synthetic-storage-secret",
                "--entrypoint",
                "sh",
                "scope-guard-s3-test:release20250422",
                "-c",
                "mkdir -p /data/startup-test; exec minio server /data",
            )
            for component, expected in CLOSURES.items():
                if component == "postgres":
                    continue
                compose("stop", "app", "backend", "llm-worker", "export-worker")
                saved = dict(environment)
                try:
                    for key in unrelated.get(component, ()):
                        environment.pop(key, None)
                    compose("up", "-d", "--no-build", "--wait", entry=f"compose.{component}.yaml")
                finally:
                    environment.clear()
                    environment.update(saved)
                running = set(compose("ps", "--services", "--status", "running").stdout.split())
                assert running == expected - {"migrate"}
                selected_postgres = compose("ps", "-q", "postgres").stdout.strip()
                assert selected_postgres == postgres_id, (
                    f"PostgreSQL recreated after {component}: {postgres_id} -> {selected_postgres}"
                )
            results.append("every component starts exactly its dependency closure")
            compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "180")
            assert compose("ps", "-q", "postgres").stdout.strip() == postgres_id
            assert (
                run("docker", "inspect", "--format", "{{json .Mounts}}", postgres_id).stdout
                == mounts
            )
            head = sql("SELECT version_num FROM alembic_version")
            assert head == "0011_password_recovery"
            assert "migration_complete" in logs()
            # Migration may have been rerun as a no-op by later component commands.
            assert "migration_start" in logs()
            run(
                os.sys.executable,
                str(root / "scripts/verify_mailpit.py"),
                "--project",
                project,
                "--client-image",
                api_image,
            )
            for worker in ("llm-worker", "export-worker"):
                assert "worker_ready" in logs(worker)
            results.append(
                "fresh complete stack healthy; component/full volume and database reused"
            )

            import httpx

            port = compose("port", "app", "3000").stdout.strip().rsplit(":", 1)[1]
            assert int(port) == frontend_port
            with httpx.Client(base_url="http://127.0.0.1:" + port, trust_env=False) as client:
                registered = client.post(
                    "/api/auth/register",
                    json={"email": "startup@example.test", "password": "12345678", "locale": "en"},
                )
                assert registered.status_code == 201
                user = registered.json()["user"]
                assert user["workspaceAccess"] == "email_confirmation_required"
                assert registered.json()["emailConfirmation"]["status"] == "accepted"
                pending = client.get("/api/v2/profile/onboarding")
                assert pending.status_code == 403
                assert pending.json() == {"error": "errors.emailVerificationRequired"}
                mail_port = compose("port", "mailpit", "8025").stdout.strip().rsplit(":", 1)[1]
                with httpx.Client(
                    base_url="http://127.0.0.1:" + mail_port, trust_env=False
                ) as mail:
                    confirmation = wait_for_confirmation(
                        mail, user["email"], public_origin, user["id"]
                    )
                assert client.get("/confirm-email").status_code == 200
                assert client.get("/api/auth/me").json()["user"]["workspaceAccess"] == (
                    "email_confirmation_required"
                )
                with httpx.Client(base_url=public_origin, trust_env=False) as another_browser:
                    confirmed = another_browser.post("/api/auth/email/confirm", json=confirmation)
                    assert confirmed.status_code == 200
                    assert "scg_session=" not in confirmed.headers.get("set-cookie", "")
                    assert another_browser.get("/api/auth/me").status_code == 401
                assert client.get("/api/auth/me").json()["user"]["workspaceAccess"] == "allowed"
                # Prove the same link was not consumed by GET, and is single-use after POST.
                assert client.post("/api/auth/email/confirm", json=confirmation).status_code == 400
                compose("stop", "mailpit")
                assert client.get("/api/v2/profile/onboarding").status_code == 200
                response = client.post(
                    "/api/v2/projects",
                    json={
                        "operationId": str(uuid4()),
                        "name": "Startup fixture",
                        "industry": "Design",
                        "scope": "Design five agreed pages; no new integrations.",
                        "startDate": "2026-10-01",
                        "pricingModel": "hourly",
                        "currency": "USD",
                        "hourlyRate": "100",
                        "fixedPrice": None,
                        "clientEmail": "client@example.test",
                        "endDate": "2026-12-15",
                    },
                )
                assert response.status_code == 201, response.text
                identifier = response.json()["project"]["id"]
                draft = client.get(f"/api/v2/projects/{identifier}/draft").json()["draft"]
                response = client.put(
                    "/api/v2/drafts/" + draft["id"],
                    json={
                        "operationId": str(uuid4()),
                        "expectedRevision": draft["revision"],
                        "patch": {"requestText": "Confirmed Docker save"},
                        "reason": "autosave",
                    },
                )
                assert response.status_code == 200, response.text
                assert (
                    client.get("/api/v2/drafts/" + draft["id"]).json()["draft"]["requestText"]
                    == "Confirmed Docker save"
                )
            results.append(
                "pending registration, captured confirmation POST "
                "and onboarding through frontend proxy"
            )
            results.append("project and draft confirmed save/read through frontend proxy")
            assert "migration_noop" in wait_exit(migrate_run())
            results.append("already-current successful no-op")

            sql("CREATE DATABASE scg_test_concurrent")
            concurrent_url = (
                "postgres://scopeguard:scopeguard_dev_password@postgres/scg_test_concurrent"
            )
            compose(
                "run",
                "--rm",
                "--no-deps",
                "-e",
                "SCOPE_GUARD_DATABASE_URL=" + concurrent_url,
                "--entrypoint",
                "python",
                "migrate",
                "-m",
                "scope_guard.database.cli",
                "migrate",
                "--database-url-env",
                "SCOPE_GUARD_DATABASE_URL",
                "--target",
                "0007_nonblocking_llm",
            )

            holder = compose(
                "run",
                "-d",
                "--no-deps",
                "--entrypoint",
                "python",
                "-e",
                "SCOPE_GUARD_DATABASE_URL=" + concurrent_url,
                "migrate",
                "-u",
                "-c",
                "import os,time,psycopg; "
                "c=psycopg.connect(os.environ['SCOPE_GUARD_DATABASE_URL']); "
                "c.execute('SELECT pg_advisory_xact_lock(642000001)'); "
                "print('held',flush=True); time.sleep(120)",
            ).stdout.strip()
            wait_log(holder, "held")
            timeout_logs = wait_exit(
                migrate_run(
                    "-e",
                    "SCOPE_GUARD_DATABASE_URL=" + concurrent_url,
                    "-e",
                    "SCOPE_GUARD_MIGRATION_LOCK_TIMEOUT_SECONDS=0.5",
                ),
                "1",
            )
            assert (
                "migration_lock_timeout" in timeout_logs
                and "migration_lock_waiting" in timeout_logs
            )
            first = migrate_run("-e", "SCOPE_GUARD_DATABASE_URL=" + concurrent_url)
            second = migrate_run("-e", "SCOPE_GUARD_DATABASE_URL=" + concurrent_url)
            wait_log(first, "migration_lock_waiting")
            wait_log(second, "migration_lock_waiting")
            run("docker", "kill", holder)
            contender_logs = [wait_exit(first), wait_exit(second)]
            assert sum("migration_noop" in item for item in contender_logs) == 1
            assert sum("migration_revision_applied" in item for item in contender_logs) == 1
            assert sum("source=0007_nonblocking_llm" in item for item in contender_logs) == 1
            assert sum(f"source={head}" in item for item in contender_logs) == 1
            results.append("bounded timeout; concurrent migration processes serialize and recheck")

            # Terminate an actual migration after DDL, using a temporary Alembic hook.
            sql("CREATE DATABASE scg_test_termination")
            hook = Path(directory) / "env.py"
            source = (root / "backend/alembic/env.py").read_text()
            source = source.replace(
                "def revision_applied(ctx, step, heads, run_args):",
                "def revision_applied(ctx, step, heads, run_args):\n"
                "    import time\n    print('fixture_migration_holding_lock', flush=True)\n"
                "    time.sleep(120)",
            )
            hook.write_text(source)
            database = (
                "postgres://scopeguard:scopeguard_dev_password@postgres:5432/scg_test_termination"
            )
            terminated = migrate_run(
                "-e",
                "SCOPE_GUARD_DATABASE_URL=" + database,
                "-v",
                str(hook) + ":/app/backend/alembic/env.py:ro",
            )
            wait_log(terminated, "fixture_migration_holding_lock")
            run("docker", "kill", "--signal", "TERM", terminated)
            assert run("docker", "wait", terminated).stdout.strip() != "0"
            assert "migration_complete" in wait_exit(
                migrate_run("-e", "SCOPE_GUARD_DATABASE_URL=" + database)
            )
            results.append("migration process termination rolls back and releases lock")

            # Successful migration container must never suppress a release update.
            previous = compose("ps", "-aq", "migrate").stdout.strip()
            # Test the direct sequence with prepared images, without a registry pull.
            compose("stop", "app", "backend", "llm-worker", "export-worker")
            compose("up", "-d", "--no-build", "--wait", "postgres")
            compose(
                "up",
                "--no-deps",
                "--no-build",
                "--force-recreate",
                "--abort-on-container-exit",
                "--exit-code-from",
                "migrate",
                "migrate",
            )
            assert compose("ps", "-aq", "migrate").stdout.strip() != previous
            assert "migration_noop" in logs()
            compose(
                "up",
                "-d",
                "--no-deps",
                "--no-build",
                "--force-recreate",
                "--wait",
                "backend",
                "llm-worker",
                "export-worker",
            )
            compose("up", "-d", "--no-deps", "--no-build", "--force-recreate", "--wait", "app")
            assert sql("SELECT count(*) FROM users") == "1"
            assert sql("SELECT count(*) FROM provider_calls") == "0"
            results.append("maintenance update reruns migration and preserves registered account")

            # Fail actual application containers after successful migration. Only
            # image preparation is substituted: these labelled fixtures are built first.
            for failed_service, image_key in (
                ("backend", "SCOPE_GUARD_API_IMAGE"),
                ("llm-worker", "SCOPE_GUARD_WORKER_IMAGE"),
                ("app", "SCOPE_GUARD_FRONTEND_IMAGE"),
            ):
                fault_image = project + "-failed-" + failed_service + ":fixture"
                fault_file = Path(directory) / (failed_service + ".Dockerfile")
                entrypoint = (
                    ["python", "-c", "import time; time.sleep(6); raise SystemExit(17)"]
                    if failed_service != "app"
                    else ["sh", "-c", "exit 19"]
                )
                fault_file.write_text(
                    f"FROM {environment[image_key]}\nLABEL scope-guard.disposable={token}\n"
                    + "ENTRYPOINT "
                    + json.dumps(entrypoint)
                    + "\n"
                )
                run("docker", "build", "-f", str(fault_file), "-t", fault_image, directory)
                fault_images.append(fault_image)
                original_image = environment[image_key]
                environment[image_key] = fault_image
                spec = importlib.util.spec_from_file_location(
                    "stack_fault", root / "scripts/stack.py"
                )
                stack = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(stack)
                real_run, original_argv = subprocess.run, os.sys.argv
                partial_release_seen = []

                def prepared_compose(
                    command,
                    *,
                    image_key=image_key,
                    real_run=real_run,
                    failed_service=failed_service,
                    partial_release_seen=partial_release_seen,
                    **kwargs,
                ):
                    if "build" in command:
                        command = [
                            "docker",
                            "image",
                            "inspect",
                            environment[image_key],
                            worker_image,
                        ]
                    elif compose_binary and command[:2] == ["docker", "compose"]:
                        command = [str(Path(compose_binary).resolve()), *command[2:]]
                    try:
                        return real_run(
                            command,
                            cwd=root,
                            env=environment,
                            check=True,
                            capture_output=True,
                            text=True,
                            timeout=240,
                        )
                    except subprocess.CalledProcessError:
                        if "up" in command and failed_service in command:
                            peers = real_run(
                                [
                                    "docker",
                                    "ps",
                                    "--filter",
                                    "label=com.docker.compose.project=" + project,
                                    "--format",
                                    "{{.Names}}",
                                ],
                                capture_output=True,
                                text=True,
                                check=True,
                            ).stdout
                            partial_release_seen.append("-worker-" in peers or "-backend-" in peers)
                        raise

                try:
                    subprocess.run = prepared_compose
                    os.sys.argv = [
                        "stack.py",
                        "update",
                        "--project",
                        project,
                        "--env-file",
                        str(empty),
                    ]
                    assert stack.main() != 0
                finally:
                    subprocess.run, os.sys.argv = real_run, original_argv
                    environment[image_key] = original_image
                assert partial_release_seen == [True]
                assert set(compose("ps", "--services", "--status", "running").stdout.split()) == {
                    "postgres"
                }
                assert sql("SELECT count(*) FROM users") == "1"
                results.append(
                    f"failed {failed_service} startup stops all partial-release applications"
                )

            sql("CREATE DATABASE scg_test_upgrade")
            upgrade_url = "postgres://scopeguard:scopeguard_dev_password@postgres/scg_test_upgrade"
            prepared = compose(
                "run",
                "--rm",
                "--no-deps",
                "-e",
                "SCOPE_GUARD_DATABASE_URL=" + upgrade_url,
                "--entrypoint",
                "python",
                "migrate",
                "-m",
                "scope_guard.database.cli",
                "migrate",
                "--database-url-env",
                "SCOPE_GUARD_DATABASE_URL",
                "--target",
                "0007_nonblocking_llm",
            )
            assert "migration_complete" in prepared.stdout
            sql(
                "INSERT INTO users(email,password_hash) VALUES ('old@example.test','synthetic')",
                database="scg_test_upgrade",
            )
            assert "migration_revision_applied" in wait_exit(
                migrate_run("-e", "SCOPE_GUARD_DATABASE_URL=" + upgrade_url)
            )
            assert sql("SELECT email FROM users", database="scg_test_upgrade") == "old@example.test"
            results.append("previous-schema upgrade through release image preserves existing user")

            # Existing services must be stopped explicitly before a failing release stage.
            sql("CREATE TABLE unexpected_startup_fixture(id integer)")
            compose("stop", "app", "backend", "llm-worker", "export-worker")
            failed_update = compose(
                "up",
                "--no-deps",
                "--no-build",
                "--force-recreate",
                "--abort-on-container-exit",
                "--exit-code-from",
                "migrate",
                "migrate",
                check=False,
            )
            assert failed_update.returncode != 0
            assert set(compose("ps", "--services", "--status", "running").stdout.split()) == {
                "postgres"
            }
            results.append("failed maintenance migration leaves existing applications stopped")

            # Recreate containers with the same disposable volume to prove fresh gates.
            compose("down")
            original_volume = json.loads(mounts)[0]["Name"]
            environment["SCOPE_GUARD_POSTGRES_VOLUME_EXTERNAL"] = "true"
            environment["SCOPE_GUARD_POSTGRES_VOLUME"] = project + "-absent"
            assert (
                compose(
                    "up", "-d", "--no-build", entry="compose.postgres.yaml", check=False
                ).returncode
                != 0
            )
            environment["SCOPE_GUARD_POSTGRES_VOLUME"] = original_volume
            compose("up", "-d", "--no-build", "--wait", entry="compose.postgres.yaml")
            assert sql("SELECT count(*) FROM users") == "1"
            environment.pop("SCOPE_GUARD_POSTGRES_VOLUME_EXTERNAL")
            environment.pop("SCOPE_GUARD_POSTGRES_VOLUME")
            results.append(
                "external existing-volume mapping preserves data and refuses absent volume"
            )
            failed = compose("up", "-d", "--no-build", "--wait", check=False)
            assert failed.returncode != 0
            running = set(compose("ps", "--services", "--status", "running").stdout.split())
            assert running <= {"postgres", "mailpit"} and "postgres" in running
            assert "migration_failed" in logs()
            assert "scopeguard_dev_password" not in logs()
            results.append("existing volume preserved; migration failure blocks fresh dependents")
        finally:
            assert project.startswith("scg-startup-test-") and project.endswith(token)
            environment.pop("SCOPE_GUARD_POSTGRES_VOLUME_EXTERNAL", None)
            environment.pop("SCOPE_GUARD_POSTGRES_VOLUME", None)
            owned = run(
                "docker",
                "volume",
                "inspect",
                "--format",
                '{{index .Labels "com.docker.compose.project"}}',
                project + "_scope_creep_guard_postgres",
                check=False,
            )
            if owned.returncode == 0:
                assert owned.stdout.strip() == project
            compose("down", "--remove-orphans", check=False)
            found = run(
                "docker",
                "inspect",
                "--format",
                '{{index .Config.Labels "scope-guard.disposable"}}',
                storage,
                check=False,
            )
            if found.returncode == 0:
                assert found.stdout.strip() == token
                run("docker", "rm", "-f", storage)
            network = run(
                "docker",
                "network",
                "inspect",
                "--format",
                '{{index .Labels "com.docker.compose.project"}}',
                project + "_default",
                check=False,
            )
            if network.returncode == 0:
                assert network.stdout.strip() == project
                run("docker", "network", "rm", project + "_default")
            for fixture in fault_images:
                owner = run(
                    "docker",
                    "image",
                    "inspect",
                    "--format",
                    '{{index .Config.Labels "scope-guard.disposable"}}',
                    fixture,
                )
                assert owner.stdout.strip() == token
                run("docker", "image", "rm", fixture)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-image", default="scope-guard-api:startup-test")
    parser.add_argument("--frontend-image", default="scope-guard-frontend:startup-test")
    parser.add_argument("--worker-image", default="scope-guard-worker:startup-test")
    parser.add_argument("--config-only", action="store_true")
    parser.add_argument(
        "--compose-binary", help="Checksum-verified standalone Compose for version tests"
    )
    args = parser.parse_args()
    print(json.dumps(verify(**vars(args)), indent=2))


if __name__ == "__main__":
    main()
