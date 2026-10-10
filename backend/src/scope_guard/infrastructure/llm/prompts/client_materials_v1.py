from pathlib import Path

from scope_guard.core.js_compat import stringify
from scope_guard.infrastructure.llm.prompts.analysis_v1 import render

TEMPLATE = Path(__file__).with_name("client-materials-v1.txt").read_text(encoding="utf8")


def material_messages(value: dict) -> dict:
    analysis = value["analysis"]
    applicable = analysis["verdict"] != "in_scope" and analysis.get(
        "hasAdditionalWork", analysis["verdict"] == "out_of_scope"
    )
    return {
        "instructions": render(
            TEMPLATE,
            {"@@CLIENT_LANGUAGE@@": value["clientLanguage"], "@@LOCALE@@": value["locale"]},
        ),
        "input": stringify(
            {
                "scope": value["scope"],
                "request": value["request"],
                "establishedAnalysis": analysis,
                "changeOrderApplicable": applicable,
            }
        ),
    }
