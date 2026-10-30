import pytest
from pydantic import ValidationError

from scope_guard.core.config import Settings


def test_non_email_production_roles_do_not_require_public_url():
    Settings(_env_file=None, production=True, worker_role="exports")


@pytest.mark.parametrize("url", ["https://example.test:invalid", "https://example.test:99999"])
def test_public_url_rejects_invalid_port(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, public_app_url=url)


def test_production_url_requires_https_and_local_http_is_explicit():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, production=True, public_app_url="http://localhost:3000")
    assert (
        Settings(_env_file=None, public_app_url="http://localhost:3000/").public_app_url
        == "http://localhost:3000"
    )
