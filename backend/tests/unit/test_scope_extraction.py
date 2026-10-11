import pytest


def test_pdf_limit_applies_after_trimming_empty_pages_and_nuls(monkeypatch):
    from types import SimpleNamespace

    from scope_guard.infrastructure.scope_readers import pdf
    from scope_guard.services.scope_extraction.service import extract

    monkeypatch.setattr(
        pdf,
        "PdfReader",
        lambda _: SimpleNamespace(
            is_encrypted=False,
            pages=[
                SimpleNamespace(extract_text=lambda: "x" * 100_000 + "\x00 \r\n"),
                SimpleNamespace(extract_text=lambda: ""),
            ],
        ),
    )
    result = extract("scope.pdf", "application/pdf", b"%PDF-1.7")
    assert result.text == "x" * 100_000
    assert [warning.code for warning in result.warnings] == ["pages_without_text", "nul_removed"]


def test_utf8_bom_newlines_and_nul_warning():
    from scope_guard.services.scope_extraction.service import extract

    result = extract("scope.MD", "text/markdown", b"\xef\xbb\xbfHello\r\nworld\x00 ")
    assert result.text == "Hello\nworld"
    assert result.warnings[0].code == "nul_removed"


@pytest.mark.parametrize(
    "name,mime,data,code,status",
    [
        ("x.exe", "text/plain", b"text", "scopeFileUnsupported", 415),
        ("x.pdf", "text/plain", b"text", "scopeFileUnsupported", 415),
        ("x.txt", "text/plain", b"\xff", "scopeFileEncoding", 400),
        ("x.txt", "", b" ", "scopeFileEmpty", 422),
        ("x.pdf", "application/pdf", b"broken", "scopePdfInvalid", 400),
        ("x.txt", "text/plain", b"x" * 100001, "scopeTextTooLarge", 413),
    ],
    ids=["extension", "mime", "encoding", "empty", "corrupt", "text_limit"],
)
def test_explicit_extraction_failures(name, mime, data, code, status):
    from scope_guard.services.scope_extraction.models import ExtractionError
    from scope_guard.services.scope_extraction.service import extract

    with pytest.raises(ExtractionError) as error:
        extract(name, mime, data)
    assert (error.value.code, error.value.status) == (code, status)


def test_scanned_and_encrypted_pdfs():
    from io import BytesIO

    from pypdf import PdfWriter

    from scope_guard.services.scope_extraction.models import ExtractionError
    from scope_guard.services.scope_extraction.service import extract

    writer = PdfWriter()
    writer.add_blank_page(595, 842)
    for password, code in [(None, "scopePdfNoText"), ("secret", "scopePdfEncrypted")]:
        if password:
            writer.encrypt(password)
        output = BytesIO()
        writer.write(output)
        with pytest.raises(ExtractionError, match=code):
            extract("scan.pdf", "application/pdf", output.getvalue())


def test_exact_text_and_upload_limits():
    from scope_guard.services.scope_extraction.models import ExtractionError
    from scope_guard.services.scope_extraction.service import MAX_FILE_BYTES, extract

    assert len(extract("scope.txt", "", b"x" * 100_000).text) == 100_000
    assert extract("scope.md", "application/octet-stream", b"\xef\xbb\xbftext").text == "text"
    with pytest.raises(ExtractionError, match="scopeFileTooLarge"):
        extract("scope.txt", "text/plain", b"x" * (MAX_FILE_BYTES + 1))
    # Astral characters consume two UTF-16 units, consistently with analysis.
    assert len(extract("scope.txt", "text/plain", ("😀" * 50_000).encode()).text) == 50_000
    with pytest.raises(ExtractionError, match="scopeTextTooLarge"):
        extract("scope.txt", "text/plain", ("😀" * 50_001).encode())


def test_mixed_pdf_and_page_limit():
    from io import BytesIO

    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen.canvas import Canvas

    from scope_guard.services.scope_extraction.models import ExtractionError
    from scope_guard.services.scope_extraction.service import extract

    source = BytesIO()
    canvas = Canvas(source)
    canvas.drawString(50, 700, "Editable scope")
    canvas.save()
    writer = PdfWriter()
    writer.add_page(PdfReader(source).pages[0])
    writer.add_blank_page(595, 842)
    output = BytesIO()
    writer.write(output)
    result = extract("scope.pdf", "application/pdf", output.getvalue())
    assert "Editable scope" in result.text
    assert result.warnings[0].page_numbers == [2]
    for _ in range(199):
        writer.add_blank_page(595, 842)
    output = BytesIO()
    writer.write(output)
    with pytest.raises(ExtractionError, match="scopePdfTooManyPages"):
        extract("scope.pdf", "", output.getvalue())
