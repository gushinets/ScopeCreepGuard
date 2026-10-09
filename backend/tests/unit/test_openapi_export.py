import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "export_openapi.py"


def test_export_and_freshness_check(tmp_path):
    target = tmp_path / "openapi.json"
    generated = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(target)], capture_output=True, text=True
    )
    assert generated.returncode == 0, generated.stderr
    schema = json.loads(target.read_text(encoding="utf-8"))
    assert "/health/live" in schema["paths"]

    checked = subprocess.run(
        [sys.executable, str(SCRIPT), "--check", str(target)], capture_output=True, text=True
    )
    assert checked.returncode == 0, checked.stderr

    target.write_text("{}", encoding="utf-8")
    stale = subprocess.run(
        [sys.executable, str(SCRIPT), "--check", str(target)], capture_output=True, text=True
    )
    assert stale.returncode == 1
    assert "stale" in stale.stderr.lower()


def test_missing_contract_reports_failure(tmp_path):
    checked = subprocess.run(
        [sys.executable, str(SCRIPT), "--check", str(tmp_path / "missing.json")],
        capture_output=True,
        text=True,
    )
    assert checked.returncode == 1
    assert "missing" in checked.stderr.lower()
