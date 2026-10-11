from scope_guard.services.scope_extraction.models import ExtractionError


def read_text(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeError:
        raise ExtractionError("scopeFileEncoding") from None
