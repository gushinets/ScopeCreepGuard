"""Exercise tracked Compose topology using only a newly owned stack and volume."""

import json
import os
import socket
import subprocess
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.integration


def test_profile_free_stack_migration_restart_replicas_and_failure(tmp_path):
    token = uuid4().hex
    project = "scg-boundaries-test-" + token
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("SCOPE_GUARD_", "PG"))
        and key
        not in {"DATABASE_URL", "AUTH_SECRET", "OPENAI_API_KEY", "COMPOSE_PROFILES", "COMPOSE_FILE"}
    }

    def docker(*args, timeout=600):
        result = subprocess.run(
            ["docker", *args],
            cwd=ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return (result.stdout + (result.stderr if args[0] == "logs" else "")).strip()

    # No interpolation/environment-file resolution: only tracked topology is read.
    config = json.loads(
        docker(
            "compose",
            "-f",
            "compose.yaml",
            "config",
            "--no-interpolate",
            "--no-env-resolution",
            "--format",
            "json",
        )
    )
    assert set(config["services"]) == {"postgres", "backend", "app"}
    assert all(not service.get("profiles") for service in config["services"].values())
    config.pop("name", None)
    config["networks"] = {"default": {}}
    config["volumes"] = {"test_data": {"labels": {"scope-guard.disposable": token}}}
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        frontend_port = listener.getsockname()[1]
    origin = f"http://127.0.0.1:{frontend_port}"
    secret = "compose-synthetic-secret-at-least-32-characters"
    for service in config["services"].values():
        service.pop("env_file", None)
        service["labels"] = {"scope-guard.disposable": token}
    database = "postgresql://scg_test:scg_test_password@postgres:5432/scg_test_stack"
    config["services"]["postgres"].update(
        environment={
            "POSTGRES_DB": "scg_test_stack",
            "POSTGRES_USER": "scg_test",
            "POSTGRES_PASSWORD": "scg_test_password",
        },
        ports=[],
        volumes=[{"type": "volume", "source": "test_data", "target": "/var/lib/postgresql/data"}],
    )
    config["services"]["backend"].update(
        environment={
            "SCOPE_GUARD_DATABASE_URL": database,
            "AUTH_SECRET": secret,
            "SCOPE_GUARD_PRODUCTION": "true",
            "OPENAI_API_KEY": "",
            "SCOPE_GUARD_ALLOWED_ORIGINS": json.dumps([origin]),
        },
        ports=[],
        image="scope-guard-backend:boundaries-test",
    )
    config["services"]["app"].update(
        environment={
            "NODE_ENV": "production",
            "AUTH_SECRET": secret,
            "SCOPE_GUARD_API_ORIGIN": "http://backend:8000",
            "SCOPE_GUARD_ALLOWED_ORIGINS": json.dumps([origin]),
            "OPENAI_API_KEY": "",
        },
        ports=[
            {
                "target": 3000,
                "published": str(frontend_port),
                "host_ip": "127.0.0.1",
                "protocol": "tcp",
            }
        ],
        image="scope-guard-frontend:boundaries-test",
    )
    manifest = tmp_path / "compose.json"
    manifest.write_text(json.dumps(config), encoding="utf-8")

    def compose(*args, timeout=600):
        return docker("compose", "-p", project, "-f", str(manifest), *args, timeout=timeout)

    def wait_backend():
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            identifier = compose("ps", "-q", "backend")
            if (
                identifier
                and docker("inspect", "--format", "{{.State.Health.Status}}", identifier)
                == "healthy"
            ):
                return
            time.sleep(1)
        raise AssertionError("Migrated API did not become healthy")

    try:
        compose("up", "--build", "-d", "--wait", "--wait-timeout", "180")
        wait_backend()
        assert "migration_complete" in compose("logs", "--no-color", "backend")
        with httpx.Client(base_url=origin, trust_env=False, timeout=20) as client:
            response = client.post(
                "/api/auth/register",
                headers={"Origin": origin},
                json={"email": "compose@example.test", "password": "12345678"},
            )
            assert response.status_code == 201, response.text
            cookie = response.headers["set-cookie"].split(";")[0]
            headers = {"Origin": origin, "Cookie": cookie}
            card = {
                "name": "Compose",
                "scope": "Five pages",
                "industry": "Development",
                "startDate": "2026-01-01",
                "pricingModel": "hourly",
                "currency": "EUR",
                "hourlyRate": "100",
            }
            response = client.post("/api/projects", headers=headers, json=card)
            assert response.status_code == 201, response.text
            saved = response.json()["project"]["id"]
            compose("restart", "backend")
            wait_backend()
            response = client.get("/api/projects", headers=headers)
            assert response.status_code == 200
            assert [item["id"] for item in response.json()["projects"]] == [saved]

        replicas = [
            compose("run", "-d", "--no-deps", "--name", project + f"-replica-{index}", "backend")
            for index in range(2)
        ]
        for replica in replicas:
            deadline = time.monotonic() + 60
            while "migration_complete" not in docker("logs", replica):
                assert docker("inspect", "--format", "{{.State.Running}}", replica) == "true"
                assert time.monotonic() < deadline
                time.sleep(0.5)
        revision = compose(
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "scg_test",
            "-d",
            "scg_test_stack",
            "-Atc",
            "SELECT version_num FROM alembic_version",
        )
        assert revision == "0001_existing_drizzle_schema"
        compose(
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "scg_test",
            "-d",
            "scg_test_stack",
            "-c",
            "CREATE DATABASE scg_test_invalid",
        )
        compose(
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "scg_test",
            "-d",
            "scg_test_invalid",
            "-c",
            "CREATE TABLE unexpected (id integer)",
        )
        failed = compose(
            "run",
            "-d",
            "--no-deps",
            "--name",
            project + "-invalid",
            "-e",
            "SCOPE_GUARD_DATABASE_URL=" + database.replace("scg_test_stack", "scg_test_invalid"),
            "backend",
        )
        assert docker("wait", failed, timeout=30) == "1"
        assert "legacy_adoption_required" in docker("logs", failed)
        assert "Application startup complete" not in docker("logs", failed)
    finally:
        identifiers = docker(
            "ps", "-aq", "--filter", "label=com.docker.compose.project=" + project
        ).splitlines()
        for identifier in identifiers:
            assert (
                docker(
                    "inspect",
                    "--format",
                    '{{index .Config.Labels "scope-guard.disposable"}}',
                    identifier,
                )
                == token
            )
        compose("down", "--volumes", "--remove-orphans")
