"""Self-contained A4 rendering: packaged fonts, splittable rows and numbered pages."""

from functools import lru_cache
from importlib.resources import files
from io import BytesIO
from itertools import zip_longest
from typing import cast
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    CondPageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from scope_guard.services.documents.models import DocumentError, PreparedDocument

WIDTH, HEIGHT, MARGIN = 595, 842, 48
CONTENT = WIDTH - MARGIN * 2
NAVY, INK, MUTED = "#0e1729", "#1c2638", "#616e80"
LINE, PAPER, ACCENT = "#d1d6de", "#f6f7fa", "#ed961f"


def fragment_rows(data, widths):
    """Split large cells before table layout, avoiding in-row overflow at page edges."""
    result = []
    for row in data:
        columns = []
        for cell, width in zip(row, widths, strict=True):
            pending, parts = [cell], []
            while pending:
                paragraph = pending.pop(0)
                _, height = paragraph.wrap(width - 24, 120)
                if height <= 120:
                    parts.append(paragraph)
                else:
                    split = paragraph.split(width - 24, 120)
                    if len(split) < 2:
                        raise DocumentError("pdfExportFailed", 500)
                    parts.append(split[0])
                    pending[0:0] = split[1:]
            columns.append(parts)
        result.extend(list(cells) for cells in zip_longest(*columns, fillvalue=""))
    return result


@lru_cache(maxsize=1)
def fonts() -> frozenset[int]:
    assets = files(__package__).joinpath("assets")
    for name, filename in [("Noto", "noto-sans.ttf"), ("NotoBold", "noto-sans-bold.ttf")]:
        pdfmetrics.registerFont(TTFont(name, str(assets.joinpath(filename))))
    return frozenset(cast(TTFont, pdfmetrics.getFont("Noto")).face.charToGlyph) & frozenset(
        cast(TTFont, pdfmetrics.getFont("NotoBold")).face.charToGlyph
    )


def render_pdf(document: PreparedDocument) -> bytes:
    characters = fonts()
    texts = [value for _, value in document.labels] + [
        document.reference,
        document.created_date,
        document.description,
        document.schedule,
    ]
    texts += [
        value
        for row in (
            *document.metadata,
            *document.commercial,
            *document.additional,
            *document.approval,
        )
        for value in (row.label, row.value)
    ]
    for value in texts:
        for character in value + value.upper():
            if not character.isspace() and ord(character) not in characters:
                raise DocumentError("pdfGlyphUnsupported")

    def p(value: str, size=10.5, bold=False, color=INK):
        return Paragraph(
            escape(value).replace("\n", "<br/>"),
            ParagraphStyle(
                "text",
                fontName="NotoBold" if bold else "Noto",
                fontSize=size,
                leading=size * 1.36,
                textColor=colors.HexColor(color),
                splitLongWords=True,
            ),
        )

    def rows(values, commercial=False):
        data = [
            [
                p(row.label, 9, True, MUTED),
                p(row.value, 12 if commercial else 9.5, commercial, NAVY if commercial else INK),
            ]
            for row in values
        ]
        widths = [180 if commercial else 118, CONTENT - (180 if commercial else 118)]
        table = Table(
            fragment_rows(data, widths),
            colWidths=widths,
            splitByRow=1,
            splitInRow=0,
        )
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(PAPER)),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor(LINE)),
                ]
            )
        )
        return table

    story = []
    banner_data = [
        [
            p(document.label("status"), 8.5, True, ACCENT),
            p(document.label("documentNumber"), 7.5, True, "#adb8c7"),
        ],
        [
            p(document.label("title"), 21, True, "#ffffff"),
            p(document.reference, 8.5, color="#ffffff"),
        ],
        [
            p(""),
            p(document.label("created") + "\n" + document.created_date, 8.5, color="#ffffff"),
        ],
    ]
    banner_widths = [350, CONTENT - 350]
    banner = Table(
        fragment_rows(banner_data, banner_widths),
        colWidths=banner_widths,
        splitInRow=0,
    )
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(NAVY)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, -1), (-1, -1), 4, colors.HexColor(ACCENT)),
            ]
        )
    )
    story += [
        banner,
        Spacer(1, 16),
        rows(document.metadata),
        Spacer(1, 12),
        p(document.label("introduction"), color=MUTED),
    ]

    def section(key):
        story.append(CondPageBreak(55))
        story.append(Spacer(1, 10))
        heading = Paragraph(
            escape(document.label(key).upper()),
            ParagraphStyle(
                "heading",
                fontName="NotoBold",
                fontSize=10.5,
                leading=14.3,
                textColor=colors.HexColor(NAVY),
                borderColor=colors.HexColor(ACCENT),
                borderWidth=1,
                borderPadding=6,
                spaceAfter=8,
                keepWithNext=False,
            ),
        )
        story.append(heading)

    section("requestedChange")
    story.append(p(document.description or "—"))
    section("commercialTerms")
    story.append(rows(document.commercial, True))
    section("scheduleImpact")
    story.append(p(document.schedule or "—"))
    section("additionalTerms")
    for row in document.additional:
        story += [
            CondPageBreak(32),
            p(row.label.upper(), 7.5, True, MUTED),
            p(row.value),
            Spacer(1, 3),
        ]
    if not document.additional:
        story.append(p("—"))
    section("approval")
    approval_data = [
        [p(row.label.upper(), 7.5, True, MUTED) for row in document.approval],
        [p(row.value or " ", 9.5) for row in document.approval],
    ]
    approval = Table(
        fragment_rows(approval_data, [CONTENT / 2] * 2),
        colWidths=[CONTENT / 2] * 2,
        splitInRow=0,
    )
    approval.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 18),
                ("LINEBELOW", (0, -1), (-1, -1), 0.7, colors.HexColor(MUTED)),
            ]
        )
    )
    story.append(approval)

    footer = p(document.label("draftFooter").upper(), 6.8, True, MUTED)
    _, footer_height = footer.wrap(CONTENT - 125, HEIGHT)
    footer_line = max(39, 24 + footer_height + 6)
    continuation = p(document.label("title"), 9, True, NAVY)
    _, header_height = continuation.wrap(CONTENT - 150, HEIGHT)

    class NumberedCanvas(Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.states = []

        def showPage(self):
            self.states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self.states)
            for state in self.states:
                self.__dict__.update(state)
                self.setStrokeColor(colors.HexColor(LINE))
                self.line(MARGIN, footer_line, WIDTH - MARGIN, footer_line)
                if self._pageNumber > 1:
                    continuation.drawOn(self, MARGIN, HEIGHT - 24 - header_height)
                    self.setFont("NotoBold", 8)
                    self.setFillColor(colors.HexColor(MUTED))
                    # A long reference remains fully printed in the splittable first
                    # banner; only repeat it when it fits the running header.
                    if pdfmetrics.stringWidth(document.reference, "NotoBold", 8) <= 140:
                        self.drawRightString(WIDTH - MARGIN, HEIGHT - 35, document.reference)
                    self.line(
                        MARGIN,
                        HEIGHT - 32 - header_height,
                        WIDTH - MARGIN,
                        HEIGHT - 32 - header_height,
                    )
                self.setFillColor(colors.HexColor(MUTED))
                self.setFont("NotoBold", 6.8)
                # Wrap long supplied footer labels instead of clipping them.
                footer.drawOn(self, MARGIN, 24)
                self.setFont("Noto", 7)
                self.drawRightString(
                    WIDTH - MARGIN, 24, f"{document.label('page')} {self._pageNumber} / {total}"
                )
                super().showPage()
            super().save()

    output = BytesIO()
    SimpleDocTemplate(
        output,
        pagesize=(WIDTH, HEIGHT),
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=max(52, header_height + 42),
        bottomMargin=footer_line + 19,
        title=document.label("title"),
        author="",
        pageCompression=1,
    ).build(story, canvasmaker=NumberedCanvas)
    return output.getvalue()
