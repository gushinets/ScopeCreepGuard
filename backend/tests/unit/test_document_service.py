from decimal import Decimal

import pytest
from service_fixtures import editor


@pytest.mark.parametrize(
    "language,expected",
    [("en", "October 6, 2026"), ("ru", "6 октября 2026 г."), ("es", "6 de octubre de 2026")],
)
def test_document_dates(language, expected):
    from scope_guard.integrations.documents.localization import document_date

    assert document_date("2026-10-06T23:59:59Z", language) == expected


def test_preparation_retains_overrides_and_missing_commercial_values():
    from scope_guard_api.draft_input import parse_editor

    from scope_guard.integrations.documents.preparation import prepare_document

    document = prepare_document(parse_editor(editor(additionalCost="1.005", currency="USD")))
    assert document.commercial[1].value == "1.005 USD"
    missing = prepare_document(
        parse_editor(editor(estimatedHours="", additionalCost="", currency=""))
    )
    assert [row.value for row in missing.commercial] == ["—", "—"]


@pytest.mark.parametrize(
    "amount", ["0.005", "1.005", "2.675", "9999999999999999999999999999.999", "0001.00"]
)
def test_money_interpretation_has_no_rounding_or_float(amount):
    from scope_guard.services.documents.service import money_value

    assert money_value(amount) == Decimal(amount)


def test_renderer_embeds_cyrillic_and_keeps_long_values():
    from io import BytesIO

    from pypdf import PdfReader
    from scope_guard_api.draft_input import parse_editor

    from scope_guard.integrations.documents.preparation import prepare_document
    from scope_guard.integrations.documents.renderer import render_pdf

    marker = "ПОСЛЕДНЯЯ СТРОКА"
    document = prepare_document(
        parse_editor(
            editor(
                language="ru",
                description="Дополнительная работа. " * 600 + marker,
                clientApproverName="Согласующий " * 200 + marker,
            )
        )
    )
    reader = PdfReader(BytesIO(render_pdf(document)))
    text = " ".join(page.extract_text() for page in reader.pages)
    assert len(reader.pages) > 1
    assert "Дополнительная работа" in reader.pages[0].extract_text()
    assert text.count(marker) == 2
    assert "СОГЛАСОВАНИЕ" in text


def test_unsupported_glyph_is_not_silently_replaced():
    from scope_guard_api.draft_input import parse_editor

    from scope_guard.integrations.documents.preparation import prepare_document
    from scope_guard.integrations.documents.renderer import render_pdf
    from scope_guard.services.documents.models import DocumentError

    with pytest.raises(DocumentError, match="pdfGlyphUnsupported"):
        render_pdf(prepare_document(parse_editor(editor(clientName="日本語"))))


def test_oversized_table_cells_are_fragmented_before_pagination():
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph

    from scope_guard.integrations.documents.renderer import fragment_rows

    paragraph = Paragraph("Long value " * 1000, ParagraphStyle("test", fontSize=10, leading=14))
    fragments = fragment_rows([[paragraph, Paragraph("date", ParagraphStyle("date"))]], [200, 200])
    assert len(fragments) > 2
    for row in fragments:
        for cell in row:
            if cell:
                assert cell.wrap(176, 120)[1] <= 120
