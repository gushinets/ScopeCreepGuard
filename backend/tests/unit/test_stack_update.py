"""A failed maintenance migration must leave application processes stopped."""

import importlib.util
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize("failure_stage", ["prepare", "migration"])
def test_update_failure_never_starts_new_applications(monkeypatch, failure_stage):
    location = Path(__file__).resolve().parents[3] / "scripts/stack.py"
    spec = importlib.util.spec_from_file_location("stack_update", location)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    state = {"old_running": True, "prepared": False, "new_running": False}

    def docker(command, **kwargs):
        if "build" in command:
            if failure_stage == "prepare":
                raise subprocess.CalledProcessError(7, command)
            state["prepared"] = True
        elif "stop" in command:
            assert state["prepared"]
            state["old_running"] = False
        elif "--exit-code-from" in command:
            assert not state["old_running"]
            raise subprocess.CalledProcessError(9, command)
        elif "up" in command and "backend" in command:
            state["new_running"] = True

    monkeypatch.setattr(module.subprocess, "run", docker)
    monkeypatch.setattr("sys.argv", ["stack.py", "update", "--project", "scg-test-update"])
    assert module.main() == (7 if failure_stage == "prepare" else 9)
    assert not state["new_running"]
    assert state["old_running"] == (failure_stage == "prepare")
