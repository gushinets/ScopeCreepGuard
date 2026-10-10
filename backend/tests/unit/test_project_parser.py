import json
from pathlib import Path

from scope_guard.api.project_input import parse_project
from scope_guard.modules.projects.use_cases import ProjectError


def test_frozen_typescript_project_parser():
    path = Path(__file__).resolve().parents[3] / "contracts/compatibility/any-640/projects.json"
    for case in json.loads(path.read_text(encoding="utf-8")):
        try:
            card = parse_project(case["body"])
            parsed = {
                "name": card.name,
                "scope": card.scope.text,
                "industry": card.industry.value,
                "startDate": card.dates.start.value,
                "pricingModel": card.pricing.model.value,
                "currency": card.pricing.currency.value,
                "hourlyRate": format(card.pricing.hourly_rate, ".2f")
                if card.pricing.hourly_rate is not None
                else None,
                "fixedPrice": format(card.pricing.fixed_price, ".2f")
                if card.pricing.fixed_price is not None
                else None,
            }
            if card.client.supplied:
                parsed["client"] = card.client.value
            result = {"ok": True, "project": parsed}
        except ProjectError as error:
            result = {"ok": False, "error": error.code}
        assert result == case["expected"]
