"""One-shot isolated operation. Only bounded files, never stdout/source diagnostics."""

import json
import os
import sys
from pathlib import Path

MEMORY = 512 * 1024 * 1024
MAX_OUTPUT = 16 * 1024 * 1024


def main():
    mode, source, target = sys.argv[1:]
    if os.name != "nt":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (MEMORY, MEMORY))
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT, MAX_OUTPUT))
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    try:
        raw = json.loads(Path(source).read_bytes())
        if mode == "pdf":
            from scope_guard.api.draft_input import parse_editor
            from scope_guard.domain.drafts.values import freeze_json
            from scope_guard.infrastructure.documents.renderer import render_pdf
            from scope_guard.services.documents.service import prepare_document

            result = render_pdf(
                prepare_document(
                    parse_editor(raw["changeOrder"]), freeze_json(raw.get("projectSnapshot"))
                )
            )
        elif mode == "extract":
            import base64

            from scope_guard.services.scope_extraction.models import ExtractionResponse
            from scope_guard.services.scope_extraction.service import extract

            value = extract(raw["name"], raw["mime"], base64.b64decode(raw["data"], validate=True))
            result = (
                ExtractionResponse(text=value.text, warnings=list(value.warnings))
                .model_dump_json(by_alias=True)
                .encode()
            )
        else:
            raise ValueError("invalid_operation")
        if len(result) > MAX_OUTPUT:
            raise MemoryError()
    except MemoryError:
        result = json.dumps(
            {
                "error": "scopeResourceLimit" if mode == "extract" else "pdfResourceLimit",
                "status": 413,
            }
        ).encode()
    except Exception as error:
        result = json.dumps(
            {
                "error": getattr(
                    error, "code", "scopeExtractFailed" if mode == "extract" else "pdfExportFailed"
                ),
                "status": getattr(error, "status", 500),
            }
        ).encode()
    Path(target).write_bytes(result)


if __name__ == "__main__":
    main()
