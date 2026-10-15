"""Real document headings and stage facts, without provider/network dependencies."""

import json
from copy import deepcopy
from pathlib import Path

from scope_guard.domain.change_orders.constants import LABEL_KEYS

PROSE = {
    "en": "These additions are outside the agreed scope and require a separate estimate "
    "and approval.",
    "ru": "Эти изменения выходят за рамки согласованного объёма работ "
    "и требуют отдельной оценки и согласования.",
    "es": "Estos cambios están fuera del alcance acordado y requieren una estimación "
    "independiente y aprobación.",
}


def labels(language):
    catalog = json.loads(
        (
            Path(__file__).parents[2] / "src/scope_guard/integrations/documents/labels.json"
        ).read_text(encoding="utf-8")
    )[language]
    aliases = {
        "draft": "status",
        "clientEmail": "email",
        "estimatedEffort": "effort",
        "additionalFee": "fee",
        "noAdditionalCharge": "noCharge",
    }
    result = {key: catalog[aliases.get(key, key)] for key in LABEL_KEYS if key != "hours"}
    result["hours"] = {"en": "hours", "ru": "часы", "es": "horas"}[language]
    # Numbered section headings are the renderer's established document labels.
    return result


def facts(language="en", action="check", tone="neutral"):
    return {
        "locale": "en",
        "selection": {"selectedLanguage": language},
        "action": action,
        "project": {
            "name": "Arrow",
            "scope": "Arrow and email alerts are excluded.",
            "pricingModel": "hourly",
            "hourlyRate": "30.00",
            "currency": "USD",
        },
        "request": "Please add Arrow and email alerts.",
        "analysis": {
            "verdict": "out_of_scope",
            "citations": ["Arrow and email alerts are excluded."],
            "hasAdditionalWork": True,
            "estimatedHours": 8,
            "additionalCost": "240.00",
            "currency": "USD",
        },
        "document": {
            "reply": {
                "tone": tone,
                "text": PROSE[language],
                "generated": dict.fromkeys(("warm", "neutral", "firm"), PROSE[language]),
                "language": language,
            },
            "changeOrder": None,
        },
    }


def order(language="en"):
    return deepcopy(
        {
            "scopePosition": "out_of_scope",
            "applicable": True,
            **dict.fromkeys(
                ("description", "timelineImpact", "rationale", "note"), PROSE[language]
            ),
            "additionalTerms": "",
            "labels": labels(language),
        }
    )
