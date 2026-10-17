"""Regression: separate interface analysis from client material language, offline."""

import asyncio
import json
from copy import deepcopy
from uuid import uuid4

import pytest
from fixtures.llm_review import PROSE, facts
from integration.test_llm_pipeline import output
from test_llm_review_corrections import RecordingStore, run

from scope_guard.integrations.llm.detection import select
from scope_guard.services.llm.operations import LlmOperations


@pytest.mark.parametrize(
    "locale,client_request,target",
    [
        ("ru", "build a new page for our custmores", "en"),
        ("en", "Добавьте новую страницу для наших клиентов, пожалуйста.", "ru"),
        ("en", "¿Podéis añadir una nueva página para nuestros clientes?", "es"),
        ("ru", "¿Podéis añadir una nueva página para nuestros clientes?", "es"),
    ],
)
def test_selected_targets_reach_actual_provider_payloads(locale, client_request, target):
    source = facts(target)
    source.update(locale=locale, request=client_request, selection=select(client_request, locale))
    assert source["selection"]["selectedLanguage"] == target
    if "custmores" in client_request:
        assert source["selection"]["status"] == "uncertain"
        assert source["selection"]["language"] == "en"
        assert source["selection"]["confidence"] == 0.4078
        assert source["selection"]["override"] is False
    before = deepcopy(source)
    for stage, candidate, language in (
        ("analysis", output("analysis_v1", locale, target), locale),
        ("replies", output("replies_v1", locale, target), target),
        ("change_order", output("change_order_v1", locale, target), target),
    ):
        store = RecordingStore()
        result = asyncio.run(run(stage, source, [candidate], store))
        assert len(store.calls) == 1
        provider = store.calls[0]["request"]
        instructions = "\n".join(m["content"] for m in provider.messages if m["role"] == "system")
        payload = json.loads(next(m["content"] for m in provider.messages if m["role"] == "user"))
        assert f"All prose must be in {language}." in instructions
        assert payload["locale"] == locale
        assert payload["selection"] == {"selectedLanguage": target}
        assert payload["request"] == client_request
        if stage == "analysis":
            assert result["reasoning"] == PROSE[locale]
            assert result["estimatedHours"] == 8
            assert "interface" in instructions
        elif stage == "replies":
            assert all(result[tone] == PROSE[target] for tone in ("warm", "neutral", "firm"))
        else:
            assert result["description"] == PROSE[target]
    assert source == before


@pytest.mark.parametrize("locale", ["ru", "en"])
def test_no_usable_evidence_falls_back_only_to_interface_language(locale):
    result = select("https://example.test/task/42 👍", locale)
    assert result["language"] is None
    assert result["selectedLanguage"] == locale
    assert result["status"] == "uncertain"
    assert select("👍", "invalid")["selectedLanguage"] == "en"


def test_override_beats_uncertain_english_candidate():
    result = select("build a new page for our custmores", "ru", "es")
    assert result["selectedLanguage"] == "es" and result["override"]
    assert result["language"] == "en" and result["status"] == "uncertain"
    with pytest.raises(ValueError, match="clientLanguageInvalid"):
        select("request", "en", "invalid")


def test_new_analysis_recomputes_selection_instead_of_reusing_previous_automatic_language():
    operations = LlmOperations(None, None, {}, language_selector=select)
    draft = {
        "requestText": "build a new page for our custmores",
        "draftDocument": {
            "reply": {"language": "ru"},
            "languageSelection": {"selectedLanguage": "ru", "override": False},
        },
    }
    before = deepcopy(draft)
    selected, locale = asyncio.run(
        operations.select_language(uuid4(), draft, "check", {"locale": "ru"})
    )
    assert locale == "ru" and selected["selectedLanguage"] == "en" and not selected["override"]
    manual, _ = asyncio.run(
        operations.select_language(
            uuid4(), draft, "check", {"locale": "ru", "documentLanguage": "es"}
        )
    )
    assert manual["selectedLanguage"] == "es" and manual["override"]
    assert draft == before
