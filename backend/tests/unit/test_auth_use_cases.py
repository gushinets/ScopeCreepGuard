import pytest

from scope_guard.modules.auth.use_cases import AuthError, credentials


def test_credentials_match_javascript_whitespace_utf16_and_untrimmed_password():
    assert credentials({"email": "\ufeff Owner@Example.Test \u00a0", "password": " 😀😀😀 "}) == (
        "owner@example.test",
        " 😀😀😀 ",
    )
    assert credentials({"email": "a@b.test", "password": "😀😀😀😀"})[1] == "😀😀😀😀"
    # JS whitespace does not include U+0085; don't introduce Python-only trimming.
    assert credentials({"email": "\u0085a@b.test", "password": "12345678"})[0] == "\u0085a@b.test"


@pytest.mark.parametrize(
    "body,code",
    [
        ({"email": 1, "password": 1}, "emailRequired"),
        ({"email": "bad", "password": None}, "passwordRequired"),
        ({"email": "bad", "password": "x"}, "invalidEmail"),
        ({"email": "a@b.test", "password": "😀😀😀"}, "passwordTooShort"),
    ],
)
def test_credential_error_precedence(body, code):
    with pytest.raises(AuthError) as error:
        credentials(body)
    assert error.value.status == 400
    assert error.value.code == "errors." + code
