import pytest


@pytest.mark.parametrize(
    "query",
    [
        "host=remote.example",
        "dbname=production",
        "user=owner",
        "hostaddr=192.0.2.1",
        "service=production",
    ],
)
def test_url_target_overrides_are_rejected(query):
    from scope_guard.infrastructure.database.session import normalize_url

    with pytest.raises(ValueError, match="unsupported_database_url"):
        normalize_url("postgresql://scg_test:x@127.0.0.1/scg_test_safe?" + query)


@pytest.mark.parametrize("operation", ["upgrade-empty", "adopt-baseline"])
def test_mutation_never_implicitly_uses_application_configuration(monkeypatch, capsys, operation):
    from scope_guard.infrastructure.database.cli import main

    monkeypatch.setenv("DATABASE_URL", "postgresql://owner:secret@remote/production")
    assert main([operation, "--database-url-env", "DATABASE_URL", "--disposable"]) == 1
    assert "disposable_target_required" in capsys.readouterr().err


def test_draft_request_is_trimmed_and_must_not_be_blank():
    from pydantic import ValidationError
    from test_contracts import fixture

    from scope_guard.modules.drafts.schemas import CreateDraftRequest

    body = {
        "projectId": "11111111-1111-4111-8111-111111111111",
        "idempotencyKey": "22222222-2222-4222-8222-222222222222",
        "locale": "en",
        "proof": "opaque-proof",
        "draftDocument": fixture()["document"],
        "request": "  Extra  ",
    }
    assert CreateDraftRequest.model_validate(body).request == "Extra"
    with pytest.raises(ValidationError):
        CreateDraftRequest.model_validate({**body, "request": "   "})


@pytest.mark.parametrize("operation", ["upgrade-empty", "adopt-baseline"])
@pytest.mark.parametrize("port", ["", ":5432"])
def test_inherited_pgport_is_rejected_before_engine_creation(monkeypatch, capsys, operation, port):
    from scope_guard.infrastructure.database import cli

    monkeypatch.setenv(
        "SCOPE_GUARD_TEST_DATABASE_URL", f"postgresql://scg_test:x@localhost{port}/scg_test_safe"
    )
    monkeypatch.setenv("PGPORT", "6543")
    for key in ("PGSERVICE", "PGSERVICEFILE", "PGHOSTADDR"):
        monkeypatch.delenv(key, raising=False)

    def forbidden_engine(*args, **kwargs):
        pytest.fail("Target guard must reject inherited PGPORT before constructing an engine")

    monkeypatch.setattr(cli, "create_engine", forbidden_engine)
    assert (
        cli.main([operation, "--database-url-env", "SCOPE_GUARD_TEST_DATABASE_URL", "--disposable"])
        == 1
    )
    assert "disposable_target_required" in capsys.readouterr().err
