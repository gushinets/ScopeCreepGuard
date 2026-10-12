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
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    try:
        raw = json.loads(Path(source).read_bytes())
        if mode == "pdf":
            from scope_guard.domain.drafts.validation import parse_editor
            from scope_guard.domain.drafts.values import freeze_json
            from scope_guard.integrations.documents.preparation import prepare_document
            from scope_guard.integrations.documents.renderer import render_pdf

            result = render_pdf(
                prepare_document(
                    parse_editor(raw["changeOrder"]), freeze_json(raw.get("projectSnapshot"))
                )
            )
        elif mode == "extract":
            import base64

            from scope_guard.integrations.documents.extraction import extract

            value = extract(raw["name"], raw["mime"], base64.b64decode(raw["data"], validate=True))
            result = json.dumps(value.to_dict(), ensure_ascii=False, separators=(",", ":")).encode()
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
