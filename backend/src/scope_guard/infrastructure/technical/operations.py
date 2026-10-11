import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

MAX_INPUT = 8 * 1024 * 1024
MAX_OUTPUT = 16 * 1024 * 1024


class TechnicalError(Exception):
    def __init__(self, code: str, status: int):
        self.code, self.status = code, status
        super().__init__(code)


class TechnicalOperations:
    def __init__(
        self, temp_root: Path | None = None, entry: Path | None = None, timeout: float | None = None
    ):
        self.temp_root, self.timeout = temp_root, timeout
        self.entry = entry or Path(__file__).with_name("entry.py")
        self.active = 0

    async def run(self, mode: str, data: bytes) -> bytes:
        if self.active >= 2:
            raise TechnicalError("technicalBusy", 429)
        if len(data) > MAX_INPUT:
            raise TechnicalError(
                "scopeFileTooLarge" if mode == "extract" else "pdfInputTooLarge", 413
            )
        self.active += 1
        process = None

        def close_job():
            pass

        try:
            with TemporaryDirectory(prefix="scope-guard-", dir=self.temp_root) as folder:
                source, target = Path(folder) / "input", Path(folder) / "output"
                source.write_bytes(data)
                # Python -I ignores PYTHONPATH; no application, provider or proxy secrets.
                env = {
                    key: value
                    for key, value in os.environ.items()
                    if key.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LANG", "LC_ALL"}
                }
                process = subprocess.Popen(
                    [sys.executable, "-I", str(self.entry), mode, str(source), str(target)],
                    cwd=folder,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                try:
                    if os.name == "nt":
                        from scope_guard.infrastructure.technical.windows_limits import attach_job

                        close_job = attach_job(
                            int(cast(Any, process)._handle),
                            512 * 1024 * 1024,
                        )
                    timeout = (
                        self.timeout
                        if self.timeout is not None
                        else 20
                        if mode == "extract"
                        else 30
                    )
                    try:
                        await asyncio.to_thread(process.wait, timeout=timeout)
                    except subprocess.TimeoutExpired:
                        raise TechnicalError(
                            "scopeExtractTimeout" if mode == "extract" else "pdfExportTimeout", 504
                        ) from None
                    if (
                        process.returncode != 0
                        or not target.exists()
                        or target.stat().st_size > MAX_OUTPUT
                    ):
                        raise TechnicalError(
                            "scopeResourceLimit" if mode == "extract" else "pdfResourceLimit", 413
                        )
                    result = target.read_bytes()
                    if result.startswith(b'{"error":'):
                        error = json.loads(result)
                        raise TechnicalError(error["error"], error["status"])
                    return result
                finally:
                    if process.poll() is None:
                        process.kill()
                    # Bounded wait after kill: cleanup completes even on cancellation.
                    process.wait(timeout=5)
                    close_job()
        finally:
            self.active -= 1
