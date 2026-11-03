"""Run backend pytest from any directory without developer application settings."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("SCOPE_GUARD_", "POSTGRES_"))
        and key
        not in {
            "AUTH_SECRET",
            "DATABASE_URL",
            "OPENAI_API_KEY",
            "OPENAI_MODEL",
            "PYTHONPATH",
            "PYTEST_ADDOPTS",
        }
    }
    # LiteLLM otherwise loads the developer's .env during test collection.
    environment["PYTHON_DOTENV_DISABLED"] = "1"
    environment["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    arguments = sys.argv[1:]
    if any(arg == "--basetemp" or arg.startswith("--basetemp=") for arg in arguments):
        raise SystemExit("This launcher manages its own disposable pytest basetemp.")
    with tempfile.TemporaryDirectory(prefix="scg-backend-pytest-") as directory:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", *arguments, "--basetemp", directory],
            cwd=ROOT / "backend",
            env=environment,
        )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
