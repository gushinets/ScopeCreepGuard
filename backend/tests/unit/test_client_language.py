import pytest
from pydantic import ValidationError

from scope_guard.modules.change_orders.schemas import LABEL_KEYS, ClientMaterials


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("EN", "en"),
        ("en-us", "en-US"),
        ("  EN-latn-us  ", "en-Latn-US"),
        ("RU-cyrl-ru", "ru-Cyrl-RU"),
        ("es-419", "es-419"),
        ("in-id", "id-ID"),
        ("mo-md", "ro-MD"),
        ("en-bu", "en-MM"),
        ("uk-SU", "uk-UA"),
        ("uk-172", "uk-UA"),
        ("et-810", "et-EE"),
        ("lv-SU", "lv-LV"),
        ("lt-SU", "lt-LT"),
        ("et-172", "et-RU"),
    ],
)
def test_supported_client_tags_match_frontend_canonicalization(raw, expected):
    materials = ClientMaterials.model_validate(
        {
            "clientLanguage": raw,
            "replies": {"warm": "Hello", "neutral": "Hello", "firm": "Hello"},
            "changeOrderLabels": dict.fromkeys(LABEL_KEYS, "Label"),
        }
    )
    assert materials.to_wire()["clientLanguage"] == expected


@pytest.mark.parametrize(
    "raw", ["en-Cyrl-US", "ru-Latn", "en-US-u-nu-arab", "en_US", "xx", "other", "und"]
)
def test_canonicalization_keeps_script_and_language_restrictions(raw):
    with pytest.raises(ValidationError):
        ClientMaterials.model_validate(
            {
                "clientLanguage": raw,
                "replies": {"warm": "Hello", "neutral": "Hello", "firm": "Hello"},
            }
        )
