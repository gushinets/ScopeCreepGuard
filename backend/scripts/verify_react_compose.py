"""Persistent React smoke using actual Compose definitions and exclusively owned data."""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-image", default="scope-guard-react-backend:check")
    parser.add_argument("--frontend-image", default="scope-guard-react-migration:check")
    args = parser.parse_args()
    project = "scopecreepguard-ci-react-" + uuid4().hex
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("SCOPE_GUARD_", "SCG_", "PG", "COMPOSE_"))
        and key not in ("DATABASE_URL", "AUTH_SECRET", "OPENAI_API_KEY")
    }
    env.update(
        AUTH_SECRET="react-compose-disposable-secret-at-least-32-characters",
        POSTGRES_PORT="0",
        FRONTEND_PORT="0",
        BACKEND_PORT="0",
    )

    def run(*command):
        return subprocess.check_output(command, cwd=ROOT, env=env, text=True).strip()

    config = json.loads(
        run(
            "docker",
            "compose",
            "-f",
            "compose.yaml",
            "config",
            "--no-env-resolution",
            "--format",
            "json",
        )
    )
    config.pop("name", None)
    for service in config["services"].values():
        service.pop("env_file", None)
        service.pop("build", None)
    config["services"]["app"]["image"] = args.frontend_image
    backend = config["services"]["backend"]
    backend["image"] = args.backend_image
    backend["environment"] = {
        "AUTH_SECRET": env["AUTH_SECRET"],
        "SCOPE_GUARD_DATABASE_URL": "postgresql://scopeguard:scopeguard_dev_password@postgres:5432/scope_creep_guard",
        "SCOPE_GUARD_PRODUCTION": "false",
        "SCOPE_GUARD_WORKFLOW_V2": "true",
        "SCOPE_GUARD_LLM_WORKFLOW": "false",
        "SCOPE_GUARD_MIGRATION_TARGET": "0008_contextual_onboarding",
        "SCOPE_GUARD_OPENAI_API_KEY": "",
    }
    for volume in config.get("volumes", {}).values():
        volume["name"] = project + "-postgres"
    for network in config.get("networks", {}).values():
        network["name"] = project + "-network"
    with tempfile.TemporaryDirectory(prefix="scg-react-compose-") as directory:
        path = Path(directory) / "compose.json"
        path.write_text(json.dumps(config), encoding="utf-8")

        def compose(*command):
            return run("docker", "compose", "-p", project, "-f", str(path), *command)

        try:
            compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "180")
            port = compose("port", "app", "3000").rsplit(":", 1)[1]
            with httpx.Client(
                base_url="http://127.0.0.1:" + port, trust_env=False, timeout=20
            ) as client:
                assert client.get("/health/live").json() == {"status": "ok"}
                for route in ("/projects/new", "/history", "/drafts", "/check?draft=old"):
                    assert '<div id="root">' in client.get(route).text
                missing = client.get("/api/v2/not-a-route")
                assert missing.status_code in (401, 404), (
                    missing.status_code,
                    missing.text,
                    compose("logs", "--tail", "15", "app", "backend"),
                )
                assert missing.headers["content-type"].startswith("application/json")
                response = client.post(
                    "/api/auth/register",
                    json={"email": "compose-react@example.test", "password": "synthetic-password"},
                )
                assert response.status_code == 201, response.text
                assert client.get("/api/auth/me").status_code == 200
                response = client.post(
                    "/api/v2/projects",
                    json={
                        "operationId": str(uuid4()),
                        "name": "Compose fixture",
                        "industry": "Design",
                        "scope": (
                            "Design five agreed pages. "
                            "E-commerce and new integrations are excluded."
                        ),
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
                        "patch": {"requestText": "Compose confirmed save"},
                        "reason": "autosave",
                    },
                )
                assert response.status_code == 200, response.text
                assert (
                    client.get("/api/v2/drafts/" + draft["id"]).json()["draft"]["requestText"]
                    == "Compose confirmed save"
                )
            print(
                json.dumps(
                    {
                        "composeProject": project,
                        "checks": 11,
                        "persistentWorkflow": True,
                        "disposableOnly": True,
                    }
                )
            )
        finally:
            assert project.startswith("scopecreepguard-ci-react-")
            for identifier in compose("ps", "-a", "-q").split():
                label = run(
                    "docker",
                    "inspect",
                    "--format",
                    '{{index .Config.Labels "com.docker.compose.project"}}',
                    identifier,
                )
                assert label == project
            compose("down", "--volumes", "--remove-orphans")


if __name__ == "__main__":
    main()
