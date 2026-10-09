"""Freeze/check contracts in owned databases only; no application configuration."""

import argparse
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "tests"))
from integration.support import DisposablePostgres, replay_drizzle  # noqa: E402


@contextmanager
def auth_server(env):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "tests/http_auth_app.py",
                str(port),
            ],
            cwd=ROOT / "backend",
            env=env,
            stdout=log,
            stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            origin = f"http://127.0.0.1:{port}"
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError("Owned authentication server failed to start")
                try:
                    with urllib.request.urlopen(origin + "/health/live", timeout=0.5):
                        break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Owned authentication server startup timed out")
            yield origin
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update-fixtures", action="store_true")
    parser.add_argument("--suite", choices=("contracts", "frontend"), default="contracts")
    args = parser.parse_args()
    with DisposablePostgres() as server, server.database() as url, server.database() as legacy_url:
        replay_drizzle(url)
        env = dict(os.environ)
        env.update(
            SCG_COMPATIBILITY_DATABASE_URL=url,
            SCG_UPDATE_COMPATIBILITY="1" if args.update_fixtures else "0",
            TEST_DATABASE_URL=legacy_url if args.suite == "frontend" else "",
            DATABASE_URL="",
            OPENAI_API_KEY="",
            SCOPE_GUARD_DATABASE_URL=url,
            AUTH_SECRET="any640-synthetic-contract-secret-at-least-32-characters",
            SCOPE_GUARD_PRODUCTION="false",
        )
        # Invoke Node directly: no shell interpretation of the generated URL.
        with auth_server(env) as origin:
            env["SCOPE_GUARD_API_ORIGIN"] = origin
            completed = subprocess.run(
                ["node", "node_modules/vitest/vitest.mjs", "run"]
                + ([] if args.suite == "frontend" else ["tests/api-compatibility.test.ts"]),
                cwd=ROOT / "frontend",
                env=env,
                check=False,
            )
        if completed.returncode:
            return completed.returncode
    return subprocess.run(
        [sys.executable, "-m", "pytest", "tests/unit/test_http_contracts.py", "-q"],
        cwd=ROOT / "backend",
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
