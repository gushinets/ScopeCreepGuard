import asyncio

import pytest


@pytest.mark.parametrize("failure", [None, "database", "worker"])
def test_email_health_exists_only_during_live_database_worker(tmp_path, monkeypatch, failure):
    from scope_guard import email_worker

    marker = tmp_path / "email-ready"
    monkeypatch.setattr(email_worker, "Path", lambda _: marker, raising=False)

    class Connection:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def execute(self, _statement):
            if failure == "database":
                raise RuntimeError("synthetic database unavailable")

    class Engine:
        def connect(self):
            return Connection()

    class Database:
        engine = Engine()

    class Worker:
        async def run(self):
            if failure == "database":
                await asyncio.Event().wait()
            assert marker.exists()
            if failure == "worker":
                raise RuntimeError("synthetic worker failure")

    if failure:
        with pytest.raises(ExceptionGroup):
            asyncio.run(email_worker.serve(Worker(), Database()))
    else:
        asyncio.run(email_worker.serve(Worker(), Database()))
    assert not marker.exists()
