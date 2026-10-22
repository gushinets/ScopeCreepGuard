import subprocess

import pytest
from integration.test_s3_exports import docker


def test_failed_storage_build_reports_stderr(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 1, "build output", "compiler terminated: out of memory"
        ),
    )
    with pytest.raises(pytest.fail.Exception) as failure:
        docker("build", "--progress=plain")
    message = str(failure.value)
    assert "docker build failed (exit 1)" in message
    assert "build output" in message
    assert "compiler terminated: out of memory" in message


def test_successful_storage_command_returns_stripped_stdout(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "container-id\n", ""),
    )
    assert docker("run") == "container-id"
