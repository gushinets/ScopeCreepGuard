import asyncio
from tempfile import SpooledTemporaryFile

import pytest
from starlette.requests import Request

from scope_guard.api.errors import ApiError
from scope_guard.api.technical_input import scope_upload


def test_bounded_chunked_upload_closes_spool(monkeypatch):
    from starlette import formparsers

    opened = []

    def spool(*args, **kwargs):
        value = SpooledTemporaryFile(*args, **kwargs)
        opened.append(value)
        return value

    monkeypatch.setattr(formparsers, "SpooledTemporaryFile", spool)

    async def run():
        messages = iter(
            [
                {
                    "type": "http.request",
                    "body": b'--test\r\nContent-Disposition: form-data; name="file"; '
                    b'filename="a.txt"\r\nContent-Type: text/plain\r\n\r\na',
                    "more_body": True,
                },
                {
                    "type": "http.request",
                    "body": b"x" * (5 * 1024 * 1024 + 65536),
                    "more_body": False,
                },
            ]
        )

        async def receive():
            return next(messages)

        request = Request(
            {"type": "http", "headers": [(b"content-type", b"multipart/form-data; boundary=test")]},
            receive,
        )
        with pytest.raises(ApiError) as error:
            await scope_upload(request)
        assert error.value.status == 413
        assert opened and all(value.closed for value in opened)

    asyncio.run(run())


def test_disconnect_closes_partial_upload(monkeypatch):
    from starlette import formparsers
    from starlette.requests import ClientDisconnect

    opened = []

    def spool(*args, **kwargs):
        value = SpooledTemporaryFile(*args, **kwargs)
        opened.append(value)
        return value

    monkeypatch.setattr(formparsers, "SpooledTemporaryFile", spool)

    async def run():
        messages = iter(
            [
                {
                    "type": "http.request",
                    "body": b'--test\r\nContent-Disposition: form-data; name="file"; '
                    b'filename="a.txt"\r\n\r\npartial',
                    "more_body": True,
                },
                {"type": "http.disconnect"},
            ]
        )

        async def receive():
            return next(messages)

        request = Request(
            {"type": "http", "headers": [(b"content-type", b"multipart/form-data; boundary=test")]},
            receive,
        )
        with pytest.raises(ClientDisconnect):
            await scope_upload(request)
        assert opened and all(value.closed for value in opened)

    asyncio.run(run())
