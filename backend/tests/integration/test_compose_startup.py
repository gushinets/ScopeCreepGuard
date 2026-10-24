"""Validate full/component Compose contracts; runtime lifecycle is ci/scripts/smoke-compose.sh."""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[3]


def test_authoritative_component_and_production_configuration():
    subprocess.run(
        [sys.executable, str(ROOT / "backend/scripts/verify_docker_startup.py"), "--config-only"],
        cwd=ROOT,
        check=True,
    )
