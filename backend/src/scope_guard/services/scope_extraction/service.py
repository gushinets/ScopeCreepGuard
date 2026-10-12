from pathlib import PurePath

from scope_guard.domain.shared.js_compat import utf16_length
from scope_guard.infrastructure.scope_readers.pdf import read_pdf
from scope_guard.infrastructure.scope_readers.text import read_text
from scope_guard.services.scope_extraction.models import (
    ExtractionError,
    ExtractionResult,
    NulRemoved,
)

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_BODY_BYTES = MAX_FILE_BYTES + 64 * 1024
ACCEPTED = {
    ".txt": {"text/plain"},
    ".md": {"text/plain", "text/markdown", "text/x-markdown"},
    ".pdf": {"application/pdf"},
}


def extract(name: str, content_type: str, data: bytes) -> ExtractionResult:
    if len(data) > MAX_FILE_BYTES:
        raise ExtractionError("scopeFileTooLarge", 413)
    extension = PurePath(name).suffix.lower()
    mime = content_type.split(";")[0].strip().lower()
    if extension not in ACCEPTED or mime not in ACCEPTED[extension] | {
        "",
        "application/octet-stream",
    }:
        raise ExtractionError("scopeFileUnsupported", 415)
    warnings: tuple = ()
    if extension == ".pdf":
        text, warnings = read_pdf(data)
    else:
        # Do not interpret a mislabelled PDF as plaintext under an ambiguous MIME.
        if data.startswith(b"%PDF-"):
            raise ExtractionError("scopeFileUnsupported", 415)
        text = read_text(data)
    if "\x00" in text:
        warnings += (NulRemoved(),)
    text = text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise ExtractionError("scopeFileEmpty", 422)
    if utf16_length(text) > 100_000:
        raise ExtractionError("scopeTextTooLarge", 413)
    return ExtractionResult(text, warnings)
