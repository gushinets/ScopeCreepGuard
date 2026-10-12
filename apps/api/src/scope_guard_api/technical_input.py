"""Bounded transport input for new technical operations, including chunked bodies."""

import asyncio
import json

from fastapi import Request
from scope_guard.services.scope_extraction.service import MAX_BODY_BYTES, MAX_FILE_BYTES
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from scope_guard_api.errors import ApiError, ErrorCode


async def bounded_stream(request: Request, limit: int, code: ErrorCode):
    count = 0
    async for chunk in request.stream():
        count += len(chunk)
        if count > limit:
            raise ApiError(code, 413)
        yield chunk


async def preview_body(request: Request) -> dict:
    try:
        async with asyncio.timeout(30):
            data = b"".join(
                [
                    chunk
                    async for chunk in bounded_stream(
                        request, 1_000_000, ErrorCode.pdf_input_too_large
                    )
                ]
            )
        raw = json.loads(data, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if not isinstance(raw, dict):
            raise ValueError()
        return raw
    except (ValueError, UnicodeError, RecursionError):
        raise ApiError(ErrorCode.request_body_invalid) from None
    except TimeoutError:
        raise ApiError(ErrorCode.pdf_export_timeout, 504) from None


async def scope_upload(request: Request) -> tuple[str, str, bytes]:
    parser = MultiPartParser(
        request.headers,
        bounded_stream(request, MAX_BODY_BYTES, ErrorCode.scope_file_too_large),
        max_files=1,
        max_fields=0,
        max_part_size=MAX_BODY_BYTES,
    )
    form = None
    try:
        async with asyncio.timeout(30):
            form = await parser.parse()
            items = form.multi_items()
            if len(items) != 1 or items[0][0] != "file" or not isinstance(items[0][1], UploadFile):
                raise ApiError(ErrorCode.request_body_invalid)
            upload = items[0][1]
            data = await upload.read(MAX_FILE_BYTES + 1)
            if len(data) > MAX_FILE_BYTES:
                raise ApiError(ErrorCode.scope_file_too_large, 413)
            return upload.filename or "", upload.content_type or "", data
    except (MultiPartException, ValueError):
        raise ApiError(ErrorCode.request_body_invalid) from None
    except TimeoutError:
        raise ApiError(ErrorCode.scope_extract_timeout, 504) from None
    finally:
        if form is not None:
            await form.close()
        # Starlette closes on MultiPartException, but not arbitrary exceptions or
        # cancellation raised by the bounded stream. Close all parser-owned files.
        for resource in parser._files_to_close_on_error:
            resource.close()
