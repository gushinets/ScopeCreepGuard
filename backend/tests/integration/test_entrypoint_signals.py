"""API entrypoint must exec its process without an independent migration child."""

import subprocess
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("signal,exit_code", [("TERM", "143"), ("INT", "130")])
def test_api_entrypoint_executes_server_and_forwards_signals(signal, exit_code):
    token = uuid4().hex

    def docker(*args):
        return subprocess.check_output(["docker", *args], cwd=ROOT, text=True).strip()

    image = "scope-guard-backend:entrypoint-test"
    docker("build", "-f", "apps/api/Dockerfile", "--target", "runner", "-t", image, ".")
    identifier = docker(
        "run",
        "-d",
        "--init",
        "--label",
        "scope-guard.disposable=" + token,
        image,
        "python",
        "-u",
        "-c",
        'import signal,time; print("server_started",flush=True); '
        "signal.signal(signal.SIGINT, lambda *a: exit(130)); time.sleep(120)",
    )
    try:
        import time

        deadline = time.monotonic() + 20
        while "server_started" not in docker("logs", identifier):
            assert time.monotonic() < deadline
            time.sleep(0.2)
        docker("kill", "--signal", signal, identifier)
        assert docker("wait", identifier) == exit_code
        assert "migration_start" not in docker("logs", identifier)
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
