import asyncio
import json
from copy import deepcopy
from pathlib import Path

import pytest
from fixtures.llm_review import facts, order
from test_llm_review_corrections import RecordingStore, run

from scope_guard.integrations.llm.stages import validate_stage


@pytest.mark.parametrize("language", ["de", "de-DE"])
def test_non_catalog_native_labels_require_contextual_language_and_semantic_review(language):
    labels = json.loads(
        (Path(__file__).parents[1] / "fixtures/german_labels.json").read_text(encoding="utf-8")
    )
    source = facts()
    source["selection"]["selectedLanguage"] = language
    prose = (
        "Diese zusätzlichen Änderungen liegen außerhalb des vereinbarten Umfangs "
        "und erfordern eine gesonderte Schätzung und Genehmigung."
    )
    candidate = {
        "scopePosition": "out_of_scope",
        "applicable": True,
        "description": prose,
        "timelineImpact": prose,
        "rationale": prose,
        "note": prose,
        "additionalTerms": "",
        "labels": labels,
    }
    store = RecordingStore()
    result = asyncio.run(run("change_order", source, [candidate], store))
    assert result["labels"] == labels
    assert "labels" in store.calls[0]["request"].schema["properties"]
    assert len(store.calls) == 1 and not store.feedbacks


@pytest.mark.parametrize(
    "language,field,heading",
    [
        ("en", "documentNumber", "Change Order Document Number"),
        ("ru", "created", "Дата создания документа"),
        ("ru", "created", "Дата составления документа"),
        ("es", "documentNumber", "Número de documento no asignado"),
        ("es", "documentNumber", "Folio de la orden de cambio"),
        ("es", "documentNumber", "Número del documento"),
    ],
)
def test_actual_acceptance_headings_are_legitimate(language, field, heading):
    candidate = order(language)
    candidate["labels"][field] = heading
    assert validate_stage("change_order", candidate, facts(language)) == candidate


@pytest.mark.parametrize("language", ["en", "ru", "es", "en-GB", "es-MX"])
def test_catalog_stage_uses_label_free_schema_and_returns_complete_labels(language):
    source = facts(language.split("-")[0])
    source["selection"]["selectedLanguage"] = language
    candidate = order(language.split("-")[0])
    candidate.pop("labels")
    store = RecordingStore()
    result = asyncio.run(run("change_order", source, [candidate], store))
    assert result["labels"]
    assert "labels" not in store.calls[0]["request"].schema["properties"]
    assert len(store.calls) == 1 and not store.feedbacks


def test_translation_d1_stale_estimate_is_rejected_and_faithful_text_passes():
    source = facts("es", "translate")
    source["selection"]["selectedLanguage"] = "en"
    source["document"]["changeOrder"] = {
        "description": "Añadir Arrow y notificaciones por correo. ¿Confirmáis el cambio? "
        "¡Gracias! Acción, revisión y coordinación.",
        "estimatedHours": "2.5",
        "additionalCost": "175.35",
        "currency": "USD",
        "timelineImpact": "3 días laborables después de la aprobación",
        "rationale": "",
        "note": "",
        "additionalTerms": "",
    }
    candidate = order()
    candidate.update(
        description="Add Arrow and email notifications. Do you confirm the change? "
        "Thank you! Action, review, and coordination.",
        timelineImpact="3 working days following approval",
        rationale="",
        note="",
        additionalTerms="",
    )
    assert validate_stage("change_order", candidate, source) == candidate
    invalid = deepcopy(candidate)
    invalid["description"] += " Estimated effort: 8 hours. Additional fee: USD 240.00."
    with pytest.raises(ValueError):
        validate_stage("change_order", invalid, source)


def test_actual_d1_second_candidate_short_business_schedule_is_not_false_rejected():
    source = facts("es", "translate")
    source["selection"]["selectedLanguage"] = "en"
    saved = order("es")
    saved.update(
        description="Añadir Arrow y notificaciones por correo. ¿Confirmáis el cambio? "
        "¡Gracias! Acción, revisión y coordinación.",
        timelineImpact="3 días laborables después de la aprobación",
    )
    source["document"]["changeOrder"] = saved
    candidate = order()
    candidate.update(
        description="Add Arrow and email notifications. Do you confirm the change? "
        "Thank you! Action, review, and coordination.",
        timelineImpact="3 business days after approval",
    )
    assert validate_stage("change_order", candidate, source) == candidate


@pytest.mark.parametrize(
    "original,translated",
    [
        ("El importe es 1.175,35 USD por 2,5 horas.", "The amount is 1,175.35 USD for 2.5 hours."),
        (
            "La estimación es de tres horas y 175,35 USD.",
            "The estimate is three hours and USD 175.35.",
        ),
    ],
)
def test_translation_accepts_localized_commercial_notation(original, translated):
    source = facts("es", "translate")
    source["selection"]["selectedLanguage"] = "en"
    source["analysis"].update(
        estimatedHours=2.5 if "2,5" in original else 3,
        additionalCost="1175.35" if "1.175" in original else "175.35",
    )
    source["document"]["reply"]["text"] = (
        original + " Estos cambios requieren una estimación independiente y aprobación."
    )
    source["document"]["reply"]["generated"] = dict.fromkeys(
        ("warm", "neutral", "firm"), source["document"]["reply"]["text"]
    )
    candidate = {
        "scopePosition": "out_of_scope",
        **dict.fromkeys(
            ("warm", "neutral", "firm"),
            translated
            + " These additions require a separate estimate and approval before work begins.",
        ),
    }
    assert validate_stage("replies", candidate, source) == candidate


@pytest.mark.parametrize(
    "language,forbidden",
    [("en", "outside the agreed"), ("ru", "за пределами"), ("es", "fuera del alcance")],
)
@pytest.mark.parametrize("verdict", ["in_scope", "borderline", "out_of_scope"])
def test_composed_catalog_introduction_does_not_assert_a_scope_verdict(
    language, forbidden, verdict
):
    source = facts(language)
    source["analysis"]["verdict"] = verdict
    if verdict == "in_scope":
        source["analysis"].update(hasAdditionalWork=False, estimatedHours=0, additionalCost="0")
    prose = {
        "en": "This document records the requested work and proposed terms "
        "for client review and approval.",
        "ru": "Настоящий документ фиксирует запрошенные работы и предлагаемые условия "
        "для проверки и согласования клиентом.",
        "es": "Este documento recoge el trabajo solicitado y las condiciones propuestas "
        "para su revisión y aprobación por el cliente.",
    }[language]
    candidate = order(language)
    candidate["scopePosition"] = verdict
    candidate["applicable"] = verdict != "in_scope"
    candidate.update(dict.fromkeys(("description", "timelineImpact", "rationale", "note"), prose))
    store = RecordingStore()
    result = asyncio.run(run("change_order", source, [candidate], store))
    # These are the same composed labels presented to semantic review and publication.
    assert forbidden not in result["labels"]["introduction"]
    assert len(store.calls) == 1 and not store.feedbacks
