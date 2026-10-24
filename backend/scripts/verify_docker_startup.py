"""Verify documented Compose topology and lifecycle using disposable Docker resources."""

import argparse
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
SERVICES = {"postgres", "migrate", "backend", "app", "llm-worker", "export-worker"}
CLOSURES = {
    "postgres": {"postgres"},
    "backend": {"postgres", "migrate", "backend"},
    "frontend": {"postgres", "migrate", "backend", "app"},
    "llm-worker": {"postgres", "migrate", "llm-worker"},
    "export-worker": {"postgres", "migrate", "export-worker"},
}


def verify(*, api_image, frontend_image, worker_image, config_only=False, compose_binary=None):
    token = uuid4().hex
    project = "scg-startup-test-" + token
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
        POSTGRES_PORT="0",
        BACKEND_PORT="0",
        FRONTEND_PORT="0",
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
            list(args), cwd=ROOT, env=environment, text=True, capture_output=True, timeout=timeout
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
            files = ["-f", str(ROOT / entry)]
            return run(
                "docker",
                "compose",
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

        full = config("compose.yaml")
        assert set(full["services"]) == SERVICES
        assert full["volumes"]["scope_creep_guard_postgres"]["name"] == (
            project + "_scope_creep_guard_postgres"
        )
        for component, expected in CLOSURES.items():
            selected = config(f"compose.{component}.yaml")
            assert set(selected["services"]) == expected
            for service in expected:
                assert selected["services"][service] == full["services"][service]
            assert selected["volumes"] == full["volumes"]
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
        )
        production = config("docker-compose.dokploy.yml")
        assert set(production["services"]) == SERVICES
        for service, definition in production["services"].items():
            assert not definition.get("ports")
            assert not definition.get("env_file")
            assert definition.get("depends_on") == full["services"][service].get("depends_on")
        for key in (
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "DATABASE_URL",
            "SCOPE_GUARD_ALLOWED_ORIGINS",
        ):
            environment.pop(key)
        saved_secret = environment.pop("AUTH_SECRET")
        assert compose("config", "--quiet", check=False).returncode != 0
        assert compose("config", "--quiet", entry="compose.postgres.yaml").returncode == 0
        environment["AUTH_SECRET"] = saved_secret
        results.append("configuration: full/component equality, production, missing settings")
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
        try:
            # First use a component, establishing the same project volume/network.
            compose("up", "-d", "--no-build", "--wait", entry="compose.postgres.yaml")
            postgres_id = compose("ps", "-q", "postgres").stdout.strip()
            existing_environment = Path(directory) / "existing-project.env"
            existing_environment.write_text("COMPOSE_PROJECT_NAME=" + project + "\n")
            wrapper_status = run(
                os.sys.executable,
                str(ROOT / "scripts/stack.py"),
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
                compose("up", "-d", "--no-build", "--wait", entry=f"compose.{component}.yaml")
                running = set(compose("ps", "--services", "--status", "running").stdout.split())
                assert running == expected - {"migrate"}
            results.append("every component starts exactly its dependency closure")
            compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "180")
            assert compose("ps", "-q", "postgres").stdout.strip() == postgres_id
            assert (
                run("docker", "inspect", "--format", "{{json .Mounts}}", postgres_id).stdout
                == mounts
            )
            head = sql("SELECT version_num FROM alembic_version")
            assert head == "0008_contextual_onboarding"
            assert "migration_complete" in logs()
            # Migration may have been rerun as a no-op by later component commands.
            assert "migration_start" in logs()
            for worker in ("llm-worker", "export-worker"):
                assert "worker_ready" in logs(worker)
            results.append(
                "fresh complete stack healthy; component/full volume and database reused"
            )

            import httpx

            port = compose("port", "app", "3000").stdout.strip().rsplit(":", 1)[1]
            with httpx.Client(base_url="http://127.0.0.1:" + port, trust_env=False) as client:
                assert (
                    client.post(
                        "/api/auth/register",
                        json={"email": "startup@example.test", "password": "12345678"},
                    ).status_code
                    == 201
                )
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
            results.append("registration and onboarding through frontend proxy")
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
            assert sum("source=0008_contextual_onboarding" in item for item in contender_logs) == 1
            results.append("bounded timeout; concurrent migration processes serialize and recheck")

            # Terminate an actual migration after DDL, using a temporary Alembic hook.
            sql("CREATE DATABASE scg_test_termination")
            hook = Path(directory) / "env.py"
            source = (ROOT / "backend/alembic/env.py").read_text()
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
            assert running == {"postgres"}
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
            compose("down", "--volumes", "--remove-orphans", check=False)
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
                run("docker", "rm", "-f", "-v", storage)
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
