import logging
from io import BytesIO

from pypdf import PdfReader

from scope_guard.core.js_compat import utf16_length
from scope_guard.services.scope_extraction.models import ExtractionError, PagesWithoutText


def read_pdf(data: bytes) -> tuple[str, tuple[PagesWithoutText, ...]]:
    if b"%PDF-" not in data[:1024]:
        raise ExtractionError("scopePdfInvalid")
    # Parser diagnostics can contain source-document strings; suppress them.
    logging.getLogger("pypdf").setLevel(logging.CRITICAL)
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise ExtractionError("scopePdfEncrypted")
        if len(reader.pages) > 200:
            raise ExtractionError("scopePdfTooManyPages", 413)
        parts, empty = [], []
        count = 0
        for number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            count += utf16_length(text) + 1
            # Bound raw parser output separately; the contractual text limit is
            # applied after NUL removal, newline normalization and trimming.
            if count > 2_000_000:
                raise ExtractionError("scopeResourceLimit", 413)
            if not text.strip():
                empty.append(number)
            parts.append(text)
        result = "\n".join(parts)
        if not result.replace("\x00", "").strip():
            raise ExtractionError("scopePdfNoText", 422)
        return result, (PagesWithoutText(page_numbers=empty),) if empty else ()
    except ExtractionError:
        raise
    except MemoryError:
        raise ExtractionError("scopeResourceLimit", 413) from None
    except Exception:
        raise ExtractionError("scopePdfInvalid") from None
