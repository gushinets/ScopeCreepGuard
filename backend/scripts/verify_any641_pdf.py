"""Generate and render deterministic PDF fixtures; inspect every PNG before delivery."""

import argparse
import json
import subprocess
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from scope_guard_api.draft_input import parse_editor

from scope_guard.integrations.documents.preparation import prepare_document
from scope_guard.integrations.documents.renderer import render_pdf

ROOT = Path(__file__).parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "output/pdf/any641")
    arguments = parser.parse_args()
    arguments.output.mkdir(parents=True, exist_ok=True)
    base = json.loads(
        (ROOT / "contracts/compatibility/any-640/drafts.json").read_text(encoding="utf-8")
    )["base"]["document"]["changeOrder"]
    base.update(
        reference="CO-20261006-A1B2C3",
        providerName="North Studio LLC",
        clientName="Acme España",
        clientEmail="ana@example.com",
        clientApproverName="Ana Ruiz",
        approvalDate="2026-10-06",
        endDate="2026-11-15",
    )
    german = json.loads(
        (ROOT / "backend/tests/fixtures/document-labels-de.json").read_text(encoding="utf-8")
    )
    fixtures = {
        "en": {
            **base,
            "language": "en",
            "description": "Add a searchable news section with responsive layouts.",
            "additionalCost": "2.675",
        },
        "ru": {
            **base,
            "language": "ru",
            "description": "Добавить раздел новостей с поиском и адаптивной вёрсткой.",
            "timelineImpact": "Восемь рабочих дней.",
            "projectName": "Сайт «Север»",
        },
        "es": {
            **base,
            "language": "es",
            "description": "Añadir una sección de noticias con búsqueda y categorías.",
            "noAdditionalCharge": True,
        },
        "de": {
            **base,
            "language": "de",
            "changeOrderLabels": german,
            "description": "Zusätzliche Änderungen für Größe und Übersicht.",
        },
        "long": {
            **base,
            "language": "ru",
            "description": "Дополнительные работы с подробным описанием. " * 150 + "КОНЕЦ ОПИСАНИЯ",
            "additionalCost": "1234567890123456789012345678901234567890",
        },
        "missing": {
            **base,
            "language": "en",
            "estimatedHours": "",
            "additionalCost": "",
            "currency": "",
        },
        "oversized": {
            **base,
            "language": "en",
            "projectName": "Long project name. " * 300 + "PROJECT END",
            "clientApproverName": "Long approval. " * 300 + "APPROVAL END",
            "additionalCost": "1" * 1000 + ".005",
        },
    }
    summary = {}
    for name, raw in fixtures.items():
        target = arguments.output / (name + ".pdf")
        data = render_pdf(prepare_document(parse_editor(raw)))
        target.write_bytes(data)
        reader = PdfReader(BytesIO(data))
        count = len(reader.pages)
        if name in ("long", "oversized"):
            assert count > 1
        else:
            assert count == 1, (name, count)
        content = " ".join(" ".join(page.extract_text().split()) for page in reader.pages)
        if name == "oversized":
            assert "PROJECT END" in content and "APPROVAL END" in content
        if name == "long":
            assert "КОНЕЦ ОПИСАНИЯ" in content
        result = subprocess.run(
            ["pdftoppm", "-png", "-r", "100", str(target), str(target.with_suffix(""))],
            capture_output=True,
        )
        assert result.returncode == 0, "PDF rasterization failed"
        summary[name] = {"pages": count, "bytes": len(data)}
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
