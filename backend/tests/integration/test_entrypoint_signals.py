import os
import subprocess
import time
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("signal,exit_code", [("TERM", "143"), ("INT", "130")])
def test_entrypoint_terminates_migration_child_without_starting_server(tmp_path, signal, exit_code):
    token = uuid4().hex
    image = "scope-guard-backend:entrypoint-test"

    def docker(*args, check=True, timeout=120):
        return subprocess.run(
            ["docker", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=check,
            timeout=timeout,
        )

    docker("build", "-f", "apps/api/Dockerfile", "--target", "runner", "-t", image, ".")
    binary = tmp_path / "bin"
    binary.mkdir()
    os.chmod(tmp_path, 0o755)
    os.chmod(binary, 0o755)
    fake_python = binary / "python"
    fake_python.write_text(
        "#!/bin/sh\necho migration_started\nexec sleep 120\n", encoding="utf-8", newline="\n"
    )
    os.chmod(fake_python, 0o755)
    identifier = docker(
        "run",
        "-d",
        "--init",
        "--label",
        "scope-guard.disposable=" + token,
        "-v",
        str(tmp_path) + ":/test",
        "--entrypoint",
        "/bin/sh",
        image,
        "-c",
        "export PATH=/test/bin:/usr/bin:/bin; "
        "exec /bin/sh /app/entrypoint.sh /bin/sh -c 'echo server_started'",
    ).stdout.strip()
    try:
        deadline = time.monotonic() + 20
        while "migration_started" not in docker("logs", identifier).stdout:
            assert time.monotonic() < deadline
            time.sleep(0.2)
        docker("kill", "--signal", signal, identifier)
        assert docker("wait", identifier, timeout=10).stdout.strip() == exit_code
        assert "server_started" not in docker("logs", identifier).stdout
    finally:
        assert (
            docker(
                "inspect",
                "--format",
                '{{index .Config.Labels "scope-guard.disposable"}}',
                identifier,
            ).stdout.strip()
            == token
        )
        docker("rm", "-f", identifier)
