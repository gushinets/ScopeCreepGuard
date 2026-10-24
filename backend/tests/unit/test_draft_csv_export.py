import csv
import io

import pytest


def render(rows, locale="en"):
    from scope_guard.services.drafts.csv_export import render_drafts_csv

    data = render_drafts_csv(rows, locale)
    assert data.startswith(b"\xef\xbb\xbf")
    return list(
        csv.reader(io.StringIO(data.decode("utf-8-sig")), delimiter=";" if locale == "ru" else ",")
    )


@pytest.mark.parametrize("locale", ["en", "ru"])
def test_csv_uses_current_fields_exact_decimals_and_localized_headers(locale):
    row = {
        "id": "draft",
        "projectId": "project",
        "projectName": 'Сайт, "Website"; ✓',
        "createdAt": "2026-10-20T12:00:00.123456+03:00",
        "updatedAt": "2026-10-21T09:00:01+00:00",
        "revision": "9223372036854775806",
        "requestText": 'Two lines\nЮникод, text; "quoted"',
        "analysisResult": {"verdict": "out_of_scope", "reasoning": "Reasoning"},
        "analysisIsStale": False,
        "draftDocument": {
            "reply": {"text": "My edited reply", "language": "es"},
            "changeOrder": {
                "description": "My edited work",
                "estimatedHours": "2.50",
                "additionalCost": "123456789012345.67",
                "currency": "EUR",
                "noAdditionalCharge": False,
                "timelineImpact": "Two days",
            },
        },
    }
    rows = render([row], locale)
    assert len(rows) == 2 and len(rows[0]) == len(rows[1]) == 18
    assert rows[0][0] == ("Draft ID" if locale == "en" else "ID черновика")
    assert rows[1][2] == row["projectName"] and rows[1][6] == row["requestText"]
    assert rows[1][3] == "2026-10-20T09:00:00.123456Z"
    assert rows[1][5] == "9223372036854775806"
    assert rows[1][7] == ("Out of scope" if locale == "en" else "Выходит за рамки работ")
    assert rows[1][9] == rows[1][16] == ("No" if locale == "en" else "Нет")
    assert rows[1][10:18] == [
        "My edited reply",
        "es",
        "My edited work",
        "2.50",
        "123456789012345.67",
        "EUR",
        rows[1][16],
        "Two days",
    ]
    assert len(render([], locale)) == 1


@pytest.mark.parametrize("prefix", ["", " ", "\t", "\r\n", "\u00a0", "\u200b", "\ufeff", "\x00"])
@pytest.mark.parametrize("operator", ["=", "+", "-", "@"])
def test_csv_blocks_formulas_after_whitespace_and_control_prefixes(prefix, operator):
    source = prefix + operator + 'SUM(1,2);"danger"'
    rows = render(
        [
            {
                "projectName": source,
                "requestText": source,
                "draftDocument": {
                    "reply": {"text": source, "language": source},
                    "changeOrder": {"description": source},
                },
            }
        ]
    )
    for index in (2, 6, 10, 11, 12):
        assert rows[1][index] == "'" + source


def test_missing_analysis_and_agreement_are_blank_and_safe_text_is_unchanged():
    rows = render([{"requestText": " 'safe =value", "analysisIsStale": True}])
    assert rows[1][6] == " 'safe =value"
    assert rows[1][7:9] == ["", ""]
    assert rows[1][9] == "Yes"
    assert rows[1][10:] == [""] * 8
