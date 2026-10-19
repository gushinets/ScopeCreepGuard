"""Customer reproductions and language fixtures, using synthetic source material."""

import json

import pytest
from fixtures.llm_review import PROSE, facts

from scope_guard.integrations.llm.detection import select
from scope_guard.integrations.llm.stages import prompt, validate_stage, validate_text


@pytest.mark.parametrize("locale", ["ru", "en"])
@pytest.mark.parametrize(
    "client_request,target",
    [
        (
            "Добавьте уведомления по электронной почте. Нужна интеграция Arrow API и webhook. "
            "Пользователи должны получать сообщения об изменении цен каждый день. "
            "Please review.",
            "ru",
        ),
        (
            "Please add email alerts for price changes and integrate the existing supplier API. "
            "Users should receive notifications whenever a new price becomes available. "
            "Спасибо за помощь.",
            "en",
        ),
        ("¿Podéis añadir avisos de nuevos precios por correo electrónico para los clientes?", "es"),
        (
            "Нужны уведомления о новых ценах. https://example.test/Please-add-email-alerts "
            "alerts@example.test `sendEmailNotification(userId)`",
            "ru",
        ),
    ],
)
def test_substantive_fragment_language_selection(locale, client_request, target):
    assert select(client_request, locale)["selectedLanguage"] == target
    assert select(client_request, locale, "es")["selectedLanguage"] == "es"


@pytest.mark.parametrize("locale", ["en", "ru"])
def test_ambiguous_candidates_are_retained_and_code_only_requests_use_fallback(locale):
    for request in (
        "Please add email notifications for customers. Пожалуйста, добавьте уведомления клиентам.",
        "https://example.test/English-request alerts@example.test ```js\nsendEmail(userId)\n```",
    ):
        selection = select(request, locale)
        assert selection["status"] == "uncertain"
        assert selection["selectedLanguage"] == (selection["language"] or locale)


@pytest.mark.parametrize(
    "target,foreign",
    [
        ("en", "Сроки согласуем отдельно."),
        ("ru", "We will discuss the schedule separately."),
        ("es", "We will discuss the schedule separately."),
        ("en", "Los plazos se acordarán por separado."),
        ("ru", "Los plazos se acordarán por separado."),
        ("es", "Сроки согласуем отдельно."),
    ],
)
def test_independent_foreign_sentence_is_rejected(target, foreign):
    with pytest.raises(ValueError, match="language"):
        validate_text("text", (PROSE[target] + " ") * 5 + foreign, target, facts(target))


def test_source_neutral_values_and_verified_quote_preserve_original_model_input():
    source = facts("ru")
    source["request"] = (
        "Добавьте уведомления: https://example.test/api/SendEmail?lang=en "
        "alerts@example.test и вызов `sendEmail(userId)`."
    )
    _, encoded = prompt("analysis", source)
    assert json.loads(encoded)["request"] == source["request"]
    validate_text(
        "text",
        PROSE["ru"]
        + ' "Arrow and email alerts are excluded." '
        + "https://example.test/api alerts@example.test `sendEmail(userId)`",
        "ru",
        source,
    )
    with pytest.raises(ValueError, match="language"):
        validate_text(
            "text", PROSE["ru"] + ' "We will discuss the schedule separately."', "ru", source
        )


@pytest.mark.parametrize("suffix", ["Thank you.", "Thanks!", "  THANK YOU!  "])
def test_cosmetic_suffix_regeneration_is_rejected(suffix):
    with pytest.raises(ValueError, match="reply_similarity"):
        validate_stage(
            "reply",
            {"scopePosition": "out_of_scope", "text": PROSE["en"] + " " + suffix},
            facts(action="regenerate"),
        )


@pytest.mark.parametrize(
    "language,proposal",
    [
        (
            "en",
            "If approved and availability is confirmed, we could target tomorrow. "
            "We could offer this free of charge if you approve a separate agreement.",
        ),
        (
            "ru",
            "Если согласуете изменения и подтвердится доступность, "
            "можно запланировать работу на завтра.",
        ),
        (
            "es",
            "Si se aprueba y se confirma la disponibilidad, "
            "podríamos planificar la entrega para mañana.",
        ),
    ],
)
def test_conditional_options_are_not_locally_misread_as_promises(language, proposal):
    validate_text("text", PROSE[language] + " " + proposal, language, facts(language))


def test_explicit_saved_free_concession_does_not_change_scope():
    source = facts()
    source["document"]["changeOrder"] = {"noAdditionalCharge": True}
    validate_text(
        "text",
        "These changes are outside the agreed scope. As you decided, "
        "we can do the additional work free of charge.",
        "en",
        source,
    )


@pytest.mark.parametrize(
    "option",
    [
        "If approved and capacity is confirmed, we could target 2026-11-20.",
        "Would November 20 be suitable, subject to approval and availability?",
        "If approved, a delivery window of 2 weeks could be discussed.",
    ],
)
def test_numeric_tentative_schedule_reaches_contextual_review(option):
    validate_text("text", PROSE["en"] + " " + option, "en", facts())


@pytest.mark.parametrize(
    "client_request",
    [
        "Добавьте PostgreSQL, Docker и Kubernetes для нашего сервиса.",
        "Нужен webhook через API для новых уведомлений клиентам.",
        "Настройте email, frontend и backend для работы с Arrow.",
    ],
)
def test_technical_english_inside_russian_prose_does_not_select_english(client_request):
    selection = select(client_request, "en")
    assert selection["selectedLanguage"] == "ru"


def test_regional_supported_language_can_defer_schedule_numbers():
    source = facts()
    validate_text(
        "text",
        "Estas alterações estão fora do escopo acordado e exigem uma "
        "estimativa e aprovação separadas.",
        "pt-BR",
        source,
    )
