"""Run the documented worker component with a no-provider test-only injection."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]


def main():
    project = "scg-any764-test-" + uuid4().hex
    image = os.environ.get("SCG_ANY764_WORKER_IMAGE", "scope-guard-worker:any764-test")
    environment = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("SCOPE_GUARD_", "COMPOSE_", "PG"))
        and k not in {"OPENAI_API_KEY", "OPENAI_MODEL", "DATABASE_URL", "AUTH_SECRET"}
    }
    with tempfile.TemporaryDirectory(prefix="scg-any764-") as directory:
        empty = Path(directory) / "empty.env"
        empty.write_text("")
        environment.update(
            {
                "COMPOSE_DISABLE_ENV_FILE": "1",
                "POSTGRES_PORT": "0",
                "SCOPE_GUARD_LOCAL_ENV_FILE": str(empty),
                "SCOPE_GUARD_LOCAL_OVERRIDE_ENV_FILE": str(empty),
                "SCOPE_GUARD_BACKEND_ENV_FILE": str(empty),
                "SCOPE_GUARD_API_IMAGE": image,
                "SCOPE_GUARD_WORKER_IMAGE": image,
                "OPENAI_API_KEY": "synthetic-never-sent",
                "SCOPE_GUARD_OPENAI_MODEL": "controlled",
                "SCOPE_GUARD_LLM_INPUT_RATE_BOUND": ".000001",
                "SCOPE_GUARD_LLM_OUTPUT_RATE_BOUND": ".000002",
                "HTTP_PROXY": "",
                "HTTPS_PROXY": "",
                "ALL_PROXY": "",
            }
        )
        command = [
            "docker",
            "compose",
            "--env-file",
            str(empty),
            "-p",
            project,
            "-f",
            "deploy/compose.llm-worker.yaml",
        ]

        def run(*args):
            result = subprocess.run(
                [*args], cwd=ROOT, env=environment, text=True, capture_output=True, timeout=240
            )
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            return result.stdout.strip()

        print(
            json.dumps(
                {
                    "project": project,
                    "image": json.loads(
                        run("docker", "image", "inspect", image, "--format", "{{json .}}")
                    )["Id"],
                    "entry": "deploy/compose.llm-worker.yaml",
                    "topology": ["postgres", "migrate", "llm-worker (one-off)"],
                    "sourceOverlay": False,
                    "injection": "test-only adapter/stop observer fixture",
                }
            )
        )
        try:
            # The maintained migration gate uses the same fresh runtime's installed code.
            run(*command, "up", "-d", "--no-build", "--wait", "postgres")
            run(*command, "run", "--rm", "migrate")
            fixture = ROOT / "backend/tests/fixtures/optional_review_worker.py"
            for enabled in ("false", "true"):
                environment["SCOPE_GUARD_LLM_SEMANTIC_REVIEW_ENABLED"] = enabled
                print(
                    run(
                        *command,
                        "run",
                        "--rm",
                        "--no-deps",
                        "-e",
                        "LITELLM_LOCAL_MODEL_COST_MAP=True",
                        "-v",
                        str(fixture) + ":/tmp/review_fixture.py:ro",
                        "--entrypoint",
                        "python",
                        "llm-worker",
                        "/tmp/review_fixture.py",
                    )
                )
        finally:
            # Project-scoped containers/network only. Retain named volumes.
            run(*command, "down", "--timeout", "40")
            print("Retained disposable project volume: " + project + "_scope_creep_guard_postgres")


if __name__ == "__main__":
    main()
