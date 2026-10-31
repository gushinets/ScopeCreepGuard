"""A failed maintenance migration must leave application processes stopped."""

import importlib.util
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "failure_stage", ["prepare", "migration", "backend", "worker", "frontend", "success"]
)
def test_update_failure_never_starts_new_applications(monkeypatch, failure_stage):
    location = Path(__file__).resolve().parents[3] / "scripts/stack.py"
    spec = importlib.util.spec_from_file_location("stack_update", location)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    applications = {"app", "backend", "llm-worker", "export-worker", "email-worker"}
    state = {"running": set(applications), "prepared": False}
    exit_codes = {
        "prepare": 7,
        "migration": 9,
        "backend": 10,
        "worker": 12,
        "frontend": 11,
        "success": 0,
    }

    def docker(command, **kwargs):
        if "build" in command:
            if failure_stage == "prepare":
                raise subprocess.CalledProcessError(7, command)
            state["prepared"] = True
        elif "stop" in command:
            assert state["prepared"]
            assert set(command[command.index("stop") + 1 :]) == applications
            state["running"].clear()
        elif "--exit-code-from" in command:
            assert not state["running"]
            if failure_stage == "migration":
                raise subprocess.CalledProcessError(9, command)
        elif "up" in command and "backend" in command:
            # Detached Compose can leave successful peers running on a failed wait.
            state["running"].update({"backend", "llm-worker", "export-worker", "email-worker"})
            if failure_stage in {"backend", "worker"}:
                raise subprocess.CalledProcessError(exit_codes[failure_stage], command)
        elif "up" in command and "app" in command:
            state["running"].add("app")
            if failure_stage == "frontend":
                raise subprocess.CalledProcessError(11, command)

    monkeypatch.setattr(module.subprocess, "run", docker)
    monkeypatch.setattr("sys.argv", ["stack.py", "update", "--project", "scg-test-update"])
    assert module.main() == exit_codes[failure_stage]
    assert state["running"] == (applications if failure_stage in {"prepare", "success"} else set())


def test_cleanup_failure_preserves_original_startup_exit_code(monkeypatch, capsys):
    location = Path(__file__).resolve().parents[3] / "scripts/stack.py"
    spec = importlib.util.spec_from_file_location("stack_cleanup", location)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    startup_failed = False
    cleanup_attempted = False

    def docker(command, **kwargs):
        nonlocal startup_failed, cleanup_attempted
        if "up" in command and "backend" in command:
            startup_failed = True
            raise subprocess.CalledProcessError(17, command)
        if "stop" in command and startup_failed:
            cleanup_attempted = True
            raise subprocess.CalledProcessError(23, command)

    monkeypatch.setattr(module.subprocess, "run", docker)
    monkeypatch.setattr("sys.argv", ["stack.py", "update", "--project", "scg-test-cleanup"])
    assert module.main() == 17
    assert cleanup_attempted
    assert "Failed to stop application services" in capsys.readouterr().err


@pytest.mark.parametrize("storage_failure", [False, True])
def test_production_storage_gate_precedes_migration_and_application_start(
    monkeypatch, storage_failure
):
    location = Path(__file__).resolve().parents[3] / "scripts/stack.py"
    spec = importlib.util.spec_from_file_location("stack_production", location)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    commands = []

    def docker(command, **kwargs):
        commands.append(command)
        if storage_failure and "--exit-code-from" in command and command[-1] == "silo-init":
            raise subprocess.CalledProcessError(8, command)

    monkeypatch.setattr(module.subprocess, "run", docker)
    monkeypatch.setattr("sys.argv", ["stack.py", "update", "--production", "--project", "scg-test"])
    assert module.main() == (8 if storage_failure else 0)
    storage = next(i for i, c in enumerate(commands) if c[-1] == "silo-init")
    if storage_failure:
        assert not any(c[-1] == "migrate" for c in commands)
        assert "stop" in commands[-1]
    else:
        migration = next(i for i, c in enumerate(commands) if c[-1] == "migrate")
        applications = next(i for i, c in enumerate(commands) if "--wait" in c and "backend" in c)
        assert storage < migration < applications


@pytest.mark.parametrize("component", ["llm_worker", "export_worker", "email_worker"])
def test_worker_logs_do_not_validate_unrelated_full_stack_settings(monkeypatch, component):
    location = Path(__file__).resolve().parents[3] / "scripts/stack.py"
    spec = importlib.util.spec_from_file_location("stack_role_logs", location)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    logs_read = []

    def docker(command, **kwargs):
        # The role-only fixture config is valid; full-stack credentials are absent.
        filename = Path(command[command.index("-f") + 1]).name
        if "config" in command and filename == "compose.yaml":
            raise subprocess.CalledProcessError(2, command)
        if "logs" in command:
            logs_read.append(command[-1])

    monkeypatch.setattr(module.subprocess, "run", docker)
    monkeypatch.setattr("sys.argv", ["stack.py", "logs", component])
    assert module.main() == 0
    assert logs_read == [component.replace("_", "-")]
