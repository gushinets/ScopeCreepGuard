"""Language and commercial regressions from the reported customer cases."""

import pytest

from scope_guard.integrations.llm.detection import evidence, select
from scope_guard.integrations.llm.stages import validate_stage, validate_text


@pytest.mark.parametrize(
    "locale,client_request,target",
    [
        (
            "ru",
            "¿Podéis gestionar también los mensajes privados de Instagram y publicar los "
            "mismos contenidos en Facebook?",
            "es",
        ),
        (
            "en",
            "Добавьте, пожалуйста, поставщика Arrow и уведомления о новых ценах по "
            "электронной почте.",
            "ru",
        ),
        (
            "ru",
            "Can you add Arrow as a third supplier and send the price alerts by email as well?",
            "en",
        ),
    ],
)
def test_general_language_selection(locale, client_request, target):
    assert select(client_request, locale)["selectedLanguage"] == target
    assert select(client_request, locale, "de")["selectedLanguage"] == "de"


@pytest.mark.parametrize(
    "bad",
    [
        "Estos cambios requieren 240 horas de trabajo adicional y cuestan 8 euros, "
        "sujetos a aprobación.",
        "Estos cambios requieren 8 horas de trabajo adicional y cuestan €240, "
        "sujetos a aprobación.",
    ],
)
def test_translation_preserves_unit_and_currency_bindings(bad):
    source = (
        "These additions require 8 hours of work and cost 240 USD, subject to separate approval."
    )
    facts = {
        "locale": "en",
        "selection": {"selectedLanguage": "es"},
        "action": "translate",
        "project": {"scope": "Extra work is excluded.", "hourlyRate": "30", "currency": "USD"},
        "request": "Please add the excluded features.",
        "analysis": {
            "verdict": "out_of_scope",
            "changeOrder": {"estimatedHours": 8, "additionalCost": "240.00", "currency": "USD"},
        },
        "document": {
            "reply": {
                "tone": "neutral",
                "text": source,
                "language": "en",
                "generated": dict.fromkeys(("warm", "neutral", "firm"), source),
            },
            "changeOrder": None,
        },
    }
    with pytest.raises(ValueError, match="commercial_terms|numerical_terms"):
        validate_stage(
            "replies",
            {"scopePosition": "out_of_scope", **dict.fromkeys(("warm", "neutral", "firm"), bad)},
            facts,
        )
    correct = (
        "Estos cambios requieren 8 horas de trabajo adicional y cuestan "
        "240 dólares estadounidenses, sujetos a aprobación."
    )
    validate_stage(
        "replies",
        {"scopePosition": "out_of_scope", **dict.fromkeys(("warm", "neutral", "firm"), correct)},
        facts,
    )


@pytest.mark.parametrize("neutral", ["https://example.test/task/42", "SEO", "👍", "Hola"])
def test_short_or_neutral_detection_is_explicit(neutral):
    result = select(neutral, "ru")
    assert result["status"] == "uncertain" and result["selectedLanguage"] == "ru"


def test_calibration_related_language_spans_and_mixed_requests():
    assert (
        evidence(
            "Эти изменения выходят за рамки согласованного объёма работ "
            "и требуют отдельной оценки и согласования."
        )["status"]
        == "detected"
    )
    mixed = (
        "Please review the additional features and confirm the estimate. "
        "Пожалуйста, добавьте нового поставщика и уведомления по почте."
    )
    assert evidence(mixed)["status"] == "uncertain"


def test_wrong_language_and_historical_scope_contradictions_are_rejected():
    facts = {
        "project": {"scope": "Arrow and email alerts are excluded.", "currency": "USD"},
        "request": "Please add Arrow and email alerts.",
        "analysis": {
            "verdict": "out_of_scope",
            "estimatedHours": 8,
            "additionalCost": "240.00",
            "currency": "USD",
        },
    }
    with pytest.raises(ValueError, match="language"):
        validate_text("reply", "Это изменение не входит в согласованный объем работ.", "es", facts)
    # Actual scope claims now require the asynchronous persisted semantic review;
    # metadata alone is still checked locally before that review.
    with pytest.raises(ValueError, match="scopePosition"):
        validate_stage(
            "reply",
            {"scopePosition": "in_scope", "text": "Included work."},
            {**facts, "locale": "en", "selection": {"selectedLanguage": "en"}},
        )
    with pytest.raises(ValueError, match="numerical"):
        validate_text(
            "reply",
            "This additional work will cost 999 USD and needs separate approval.",
            "en",
            facts,
        )
    validate_text(
        "reply",
        "These additions are outside the agreed scope and require a separate estimate "
        "and approval.",
        "en",
        facts,
    )
