import pytest

from scope_guard.integrations.llm.preservation import preserve_translation


@pytest.mark.parametrize(
    "translated",
    [
        "3 días naturales después de la aprobación",
        "4 días laborables después de la aprobación",
        "3 semanas laborables después de la aprobación",
        "3 días laborables desde hoy",
    ],
)
def test_working_schedule_cannot_change_even_with_same_number(translated):
    with pytest.raises(ValueError, match="timeline_commitment"):
        preserve_translation(
            "timelineImpact", "3 working days after approval", translated, "en", "es"
        )


@pytest.mark.parametrize(
    "translated",
    ["3 días laborables después de la aprobación", "tres días hábiles tras la aprobación"],
)
def test_faithful_working_schedule_including_number_words(translated):
    preserve_translation("timelineImpact", "3 working days after approval", translated, "en", "es")


@pytest.mark.parametrize(
    "translated",
    [
        "175,36 USD y 2,5 horas",
        "175,35 EUR y 2,5 horas",
        "175,35 horas y 2,5 USD",
        "175 USD y 2,5 horas",
        "175,35 USD",
        "175,35 USD y dos horas",
    ],
)
def test_changed_rounded_removed_or_rebound_commercial_terms_rejected(translated):
    with pytest.raises(ValueError, match="commercial_terms"):
        preserve_translation("description", "175.35 USD and 2.5 hours", translated, "en", "es")


@pytest.mark.parametrize(
    "source,translated",
    [
        ("1.175,35 USD y 2,5 horas", "1,175.35 USD and 2.5 hours"),
        ("175,35 USD y tres horas", "USD 175.35 and three hours"),
        ("1 175,35 USD y 2,5 horas", "USD 1175.35 and 2.5 hours"),
        ("", ""),
    ],
)
def test_localized_binding_and_empty_fields(source, translated):
    preserve_translation("description", source, translated, "es", "en")


@pytest.mark.parametrize(
    "source,translated",
    [
        ("one hundred dollars", "100 dólares"),
        ("21 days after approval", "twenty one days after approval"),
        ("100 USD and 21 hours", "cien USD y veintiuna horas"),
        ("100 USD and 21 hours", "сто USD и двадцать один час"),
    ],
)
def test_compound_number_words(source, translated):
    target = (
        "ru"
        if "сто" in translated
        else "es"
        if "USD y" in translated or "dólares" in translated
        else "en"
    )
    preserve_translation("description", source, translated, "en", target)


def test_singular_russian_working_day_is_faithful():
    preserve_translation(
        "timelineImpact",
        "1 working day after approval",
        "1 рабочий день после согласования",
        "en",
        "ru",
    )


def test_conditional_numeric_working_schedule_reaches_bounded_review():
    from fixtures.llm_review import facts

    from scope_guard.integrations.llm.stages import validate_text

    validate_text(
        "text",
        "If approved and capacity is confirmed, we could target 3 working days.",
        "en",
        facts(),
    )
