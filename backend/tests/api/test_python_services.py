from io import BytesIO
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader
from service_fixtures import editor

from scope_guard.api.dependencies import current_owner
from scope_guard.core.config import Settings
from scope_guard.main import create_app

OWNER = "11111111-1111-4111-8111-111111111111"


def test_new_operations_authenticate_before_processing():
    app = create_app(Settings(_env_file=None))
    with TestClient(app) as client:
        for method, path in [
            ("GET", f"/api/drafts/{OWNER}/pdf"),
            ("POST", "/api/change-orders/pdf"),
            ("POST", "/api/scope/extract"),
        ]:
            response = client.request(method, path)
            assert response.status_code == 401
            assert response.json() == {"error": "errors.authRequired"}
            assert response.headers["cache-control"] == "private, no-store"


def test_scope_multipart_contract_and_validation():
    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[current_owner] = lambda: {"id": OWNER}
    with TestClient(app) as client:
        response = client.post(
            "/api/scope/extract", files={"file": ("x.md", b"Hello\x00", "text/markdown")}
        )
        assert response.status_code == 200
        assert response.json() == {"text": "Hello", "warnings": [{"code": "nul_removed"}]}
        for files, status, code in [
            ({"file": ("x.exe", b"hello", "text/plain")}, 415, "scopeFileUnsupported"),
            ({"file": ("x.txt", b"\xff", "text/plain")}, 400, "scopeFileEncoding"),
            ({"file": ("x.txt", b"", "text/plain")}, 422, "scopeFileEmpty"),
            ([("file", ("a.txt", b"a")), ("file", ("b.txt", b"b"))], 400, "requestBodyInvalid"),
        ]:
            result = client.post("/api/scope/extract", files=files)
            assert result.status_code == status
            assert result.json() == {"error": f"errors.{code}"}


@pytest.mark.parametrize("optional_draft", [{}, {"draftId": None}])
def test_unsaved_export_has_no_save_proof_or_llm(optional_draft):
    from scope_guard.api.dependencies import document_use_cases

    class UseCases:
        async def preview(self, owner, project, draft, change_order):
            assert owner == UUID(OWNER) and project == UUID(OWNER) and draft is None
            from scope_guard.services.documents.models import DocumentSource

            return DocumentSource(change_order, None)

    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[current_owner] = lambda: {"id": OWNER}
    app.dependency_overrides[document_use_cases] = UseCases
    with TestClient(app) as client:
        response = client.post(
            "/api/change-orders/pdf",
            json={
                "projectId": OWNER,
                "changeOrder": editor(additionalCost="2.675"),
                **optional_draft,
            },
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert (
            response.headers["content-disposition"]
            == f'attachment; filename="change-order-{OWNER}.pdf"'
        )
        assert "2.675" in " ".join(
            page.extract_text() for page in PdfReader(BytesIO(response.content)).pages
        )


def test_openapi_describes_pdf_and_multipart():
    schema = create_app(Settings(_env_file=None)).openapi()
    paths = schema["paths"]
    assert (
        "application/pdf"
        in paths["/api/drafts/{draftId}/pdf"]["get"]["responses"]["200"]["content"]
    )
    assert "multipart/form-data" in paths["/api/scope/extract"]["post"]["requestBody"]["content"]
