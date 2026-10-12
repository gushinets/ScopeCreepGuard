import asyncio
import json

import pytest
from service_fixtures import editor


def test_real_isolated_pdf_and_text_cleanup(tmp_path):
    from scope_guard.integrations.documents.technical.operations import TechnicalOperations

    async def run():
        service = TechnicalOperations(temp_root=tmp_path)
        pdf = await service.run(
            "pdf", json.dumps({"changeOrder": editor(), "projectSnapshot": None}).encode()
        )
        assert pdf.startswith(b"%PDF-")
        text = await service.run(
            "extract",
            json.dumps({"name": "scope.txt", "mime": "text/plain", "data": "SGVsbG8="}).encode(),
        )
        assert json.loads(text)["text"] == "Hello"
        assert list(tmp_path.iterdir()) == []
        assert service.active == 0

    asyncio.run(run())


def test_timeout_cancel_and_admission_always_clean(tmp_path):
    from scope_guard.integrations.documents.technical.operations import (
        TechnicalError,
        TechnicalOperations,
    )

    script = tmp_path / "slow.py"
    script.write_text("import time; time.sleep(60)")

    async def run():
        service = TechnicalOperations(temp_root=tmp_path, entry=script, timeout=0.1)
        with pytest.raises(TechnicalError, match="scopeExtractTimeout"):
            await service.run("extract", b"{}")
        service.timeout = 30
        first = asyncio.create_task(service.run("extract", b"{}"))
        second = asyncio.create_task(service.run("extract", b"{}"))
        while service.active < 2:
            await asyncio.sleep(0.01)
        with pytest.raises(TechnicalError, match="technicalBusy"):
            await service.run("extract", b"{}")
        first.cancel()
        second.cancel()
        for task in (first, second):
            with pytest.raises(asyncio.CancelledError):
                await task
        assert service.active == 0
        assert list(tmp_path.iterdir()) == [script]

    asyncio.run(run())


def test_child_environment_excludes_secrets(tmp_path, monkeypatch):
    from scope_guard.integrations.documents.technical.operations import TechnicalOperations

    monkeypatch.setenv("SCOPE_GUARD_DATABASE_URL", "secret")
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    script = tmp_path / "environment.py"
    script.write_text(
        "import os,sys; from pathlib import Path; "
        "Path(sys.argv[3]).write_text(','.join(os.environ))"
    )
    output = asyncio.run(
        TechnicalOperations(temp_root=tmp_path, entry=script).run("extract", b"{}")
    )
    assert b"SCOPE_GUARD_DATABASE_URL" not in output
    assert b"OPENAI_API_KEY" not in output


def test_validation_and_parser_failure_remove_operation_files(tmp_path):
    from scope_guard.integrations.documents.technical.operations import (
        TechnicalError,
        TechnicalOperations,
    )

    async def run():
        service = TechnicalOperations(temp_root=tmp_path)
        for payload, code in [
            (
                {"name": "scope.exe", "mime": "text/plain", "data": "SGVsbG8="},
                "scopeFileUnsupported",
            ),
            (
                {"name": "scope.pdf", "mime": "application/pdf", "data": "YnJva2Vu"},
                "scopePdfInvalid",
            ),
        ]:
            with pytest.raises(TechnicalError, match=code):
                await service.run("extract", json.dumps(payload).encode())
            assert service.active == 0
            assert list(tmp_path.iterdir()) == []

    asyncio.run(run())
