"""Typed fixed-stage runner with bounded PydanticAI corrections and domain checks."""

import json
import re
from decimal import Decimal
from functools import lru_cache
from importlib.resources import files
from typing import Literal

from babel.units import format_unit
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_ai import Agent, ModelRetry, NativeOutput
from pydantic_ai.exceptions import UnexpectedModelBehavior

from scope_guard.domain.llm.runtime import GatewayFailure
from scope_guard.integrations.documents.localization import reviewed_stage_labels
from scope_guard.integrations.llm.detection import clean, detector, evidence, foreign_evidence
from scope_guard.integrations.llm.preservation import (
    preserve_translation,
    recognized_schedule_language,
)
from scope_guard.integrations.llm.prompts.workflow_v2 import stage_prompt
from scope_guard.integrations.llm.pydanticai_model import GatewayResponsesModel
from scope_guard.integrations.llm.semantic_review import (
    SemanticReviewer,
    cosmetic_reply,
    without_schedule,
)
from scope_guard.integrations.llm.terms import mentions

Position = Literal["in_scope", "borderline", "out_of_scope"]


class StrictStage(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnalysisStage(StrictStage):
    verdict: Position
    confidence: int = Field(ge=0, le=100)
    summary: str = Field(min_length=1)
    reasoning: str = Field(min_length=1)
    citations: list[str]
    suggestion: str
    hasAdditionalWork: bool
    estimatedHours: float = Field(ge=0, le=10000)
    additionalCost: str = Field(pattern=r"^\d+(?:\.\d{1,2})?$")
    currency: Literal["", "RUB", "USD", "EUR"]


class RepliesStage(StrictStage):
    scopePosition: Position
    warm: str = Field(min_length=1)
    neutral: str = Field(min_length=1)
    firm: str = Field(min_length=1)


class ReplyStage(StrictStage):
    scopePosition: Position
    text: str = Field(min_length=1)


class LabelsStage(StrictStage):
    title: str
    draft: str
    documentNumber: str
    created: str
    project: str
    provider: str
    client: str
    clientEmail: str
    requestedChange: str
    commercialTerms: str
    estimatedEffort: str
    additionalFee: str
    noAdditionalCharge: str
    scheduleImpact: str
    additionalTerms: str
    approval: str
    approvedBy: str
    date: str
    draftFooter: str
    introduction: str
    outsideScopeFree: str
    endDate: str
    rationale: str
    terms: str
    note: str
    page: str
    hours: str


class ChangeOrderProseStage(StrictStage):
    scopePosition: Position
    applicable: bool
    description: str
    timelineImpact: str
    rationale: str
    note: str
    additionalTerms: str


class ChangeOrderStage(ChangeOrderProseStage):
    labels: LabelsStage


class EstimateStage(StrictStage):
    scopePosition: Position
    estimatedHours: float = Field(gt=0, le=10000)
    additionalCost: str = Field(pattern=r"^\d+(?:\.\d{1,2})?$")
    currency: Literal["RUB", "USD", "EUR"]
    rationale: str = Field(min_length=1)


TYPES = {
    "analysis": AnalysisStage,
    "replies": RepliesStage,
    "reply": ReplyStage,
    "change_order": ChangeOrderStage,
    "estimate": EstimateStage,
}


def numeric_values(value):
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return {
        Decimal(number.replace(",", "."))
        for number in re.findall(r"(?<!\w)\d+(?:[.,]\d+)?", str(value))
    }


def label_words(value):
    return re.findall(r"[^\W\d_]+", value.casefold())


@lru_cache(maxsize=26)
def label_vocabulary(target):
    """Ground ambiguous headings in the existing reviewed document translations."""
    catalog = json.loads(
        files("scope_guard.integrations.documents")
        .joinpath("labels.json")
        .read_text(encoding="utf-8")
    )
    reference = " ".join(catalog.get(target, {}).values())
    for quantity in (1, 2):
        for length in ("long", "short", "narrow"):
            reference += " " + format_unit(quantity, "duration-hour", length=length, locale=target)
    return frozenset(label_words(reference))


def label_evidence(prose, target, group, exceptions, *, reviewed_semantically=False):
    """Context disambiguates concise labels, never independently foreign evidence."""
    observed = evidence(prose, minimum_letters=1)
    spans = [
        prose[item.start_index : item.end_index]
        for item in detector().detect_multiple_languages_of(prose)
    ]
    for span in [prose, *spans, *re.split(r"[/|;:\n]", prose)]:
        independent = evidence(span, minimum_letters=1)
        if independent["status"] == "detected" and independent["language"] != target:
            return independent
        if sum(c.isalpha() for c in span) >= 4:
            scores = detector().compute_language_confidence_values(span)
            support = next(
                (s.value for s in scores if s.language.iso_code_639_1.name.lower() == target), 0
            )
            # Ambiguity between foreign languages is not evidence for the target.
            # A concise label may borrow context only if the target remains plausible.
            if scores and support < scores[0].value * 0.05:
                return independent
    if observed["status"] == "detected":
        return observed
    # Only concise headings/units may borrow context; document sentences remain strict.
    if (
        len(prose.split()) <= 8
        and len(prose) <= 100
        and (set(label_words(prose)) <= label_vocabulary(target) or reviewed_semantically)
    ):
        return evidence(group, exceptions)
    return observed


REVIEWED_HEADING_VARIANTS = {
    "en": {"Change Order Document Number"},
    "ru": {"Дата создания документа", "Дата составления документа"},
    "es": {
        "Número de documento no asignado",
        "Folio de la orden de cambio",
        "Número del documento",
    },
}


def validate_text(
    field,
    value,
    target,
    facts,
    *,
    group=None,
    analysis=False,
    check_position=True,
    label_group=None,
    reviewed_labels=False,
):
    quotes = [
        q
        for q in (facts.get("analysis") or {}).get("citations", [])
        if q and q in facts["project"]["scope"]
    ]
    project = facts["project"]
    # Exact reviewed labels need no probabilistic inference; other wording remains strict.
    if field.startswith("labels."):
        reviewed = reviewed_stage_labels(target)
        if reviewed and (
            value == reviewed.get(field.removeprefix("labels."))
            or value in REVIEWED_HEADING_VARIANTS.get(target.split("-")[0], set())
        ):
            return
    exceptions = quotes + [project.get("name") or "", project.get("clientName") or ""]
    prose = clean(value, exceptions)
    foreign = foreign_evidence(prose, target.split("-")[0])
    if foreign:
        raise ValueError(
            f"{field}.language: expected {target}; foreign prose detected "
            f"{foreign['language']}; confidence {foreign['confidence']}"
        )
    observed = (
        label_evidence(
            prose,
            target.split("-")[0],
            label_group,
            exceptions,
            reviewed_semantically=reviewed_labels,
        )
        if label_group is not None
        else evidence(prose)
    )
    if label_group is None and sum(c.isalpha() for c in prose) < 12 and group:
        observed = evidence(group, exceptions)
    if field == "timelineImpact" and recognized_schedule_language(prose, target):
        observed = {"status": "detected", "language": target.split("-")[0], "confidence": 1}
    if observed["status"] != "detected" or observed["language"] != target.split("-")[0]:
        raise ValueError(
            f"{field}.language: expected {target}; detected {observed['language']}; "
            f"confidence {observed['confidence']}; preserve facts"
        )
    if analysis:
        return
    if label_group is not None:
        # Section numbering is document structure, not a newly estimated commitment.
        value = re.sub(r"^\s*\d+[.)]\s+", "", value)
        prose = re.sub(r"^\s*\d+[.)]\s+", "", prose)
    accepted = facts.get("analysis") or {}
    terms = accepted.get("changeOrder", accepted)
    saved_order = facts.get("document", {}).get("changeOrder") or {}
    allowed_terms = {
        k: terms.get(k) for k in ("estimatedHours", "additionalCost", "currency", "timelineImpact")
    }
    if facts.get("action") != "translate" and not numeric_values(
        without_schedule(value, target)
    ) <= numeric_values([project, facts["request"], allowed_terms, saved_order]):
        raise ValueError(f"{field}.numerical_terms: an unsupported number or commitment")
    pairs = {
        (Decimal(str(v)), str(currency).upper())
        for v, currency in (
            (terms.get("additionalCost"), terms.get("currency")),
            (saved_order.get("additionalCost"), saved_order.get("currency")),
            (project.get("hourlyRate"), project.get("currency")),
            (project.get("fixedPrice"), project.get("currency")),
        )
        if v not in (None, "")
    }
    hours = {
        Decimal(str(v))
        for v in (terms.get("estimatedHours"), saved_order.get("estimatedHours"))
        if v not in (None, "")
    }
    for unit, amount in mentions(prose, target):
        if (
            unit == "hours"
            and amount not in hours
            or unit != "hours"
            and (amount, unit) not in pairs
        ):
            raise ValueError(
                f"{field}.commercial_terms: preserve accepted effort, amount and currency"
            )
    # Scope and schedule are contextual claims, not keyword properties. The persisted
    # structured review evaluates actual sentences, conditions and saved decisions.


def validate_stage(stage, data, facts, *, reviewed_labels=False):
    raw = data.model_dump() if isinstance(data, BaseModel) else data
    locale, target = facts["locale"], facts["selection"]["selectedLanguage"]
    accepted = facts.get("analysis") or {}
    if stage == "analysis":
        for field in ("summary", "reasoning", "suggestion"):
            if raw[field]:
                validate_text(
                    field,
                    raw[field],
                    locale,
                    {**facts, "analysis": {"citations": raw["citations"]}},
                    analysis=True,
                )
        if any(quote not in facts["project"]["scope"] for quote in raw["citations"]):
            raise ValueError("citations.scope: quote must be verbatim in frozen scope")
        if raw["verdict"] == "in_scope" and (
            raw["hasAdditionalWork"]
            or raw["estimatedHours"] != 0
            or Decimal(raw["additionalCost"]) != 0
        ):
            raise ValueError("analysis.scope_position: included work cannot incur additional terms")
        if raw["currency"] != (facts["project"].get("currency") or ""):
            raise ValueError("analysis.currency: preserve project currency")
        if facts["project"].get("pricingModel") == "hourly" and raw["hasAdditionalWork"]:
            estimate = Decimal(str(raw["estimatedHours"])) * Decimal(facts["project"]["hourlyRate"])
            if Decimal(raw["additionalCost"]) != estimate.quantize(Decimal(".01")):
                raise ValueError("analysis.additionalCost: hours times frozen hourly rate")
    else:
        if raw["scopePosition"] != accepted["verdict"]:
            raise ValueError("scopePosition: preserve accepted verdict")
        if stage in ("replies", "reply"):
            fields = ("warm", "neutral", "firm") if stage == "replies" else ("text",)
            for field in fields:
                if stage == "reply":
                    reply = facts["document"]["reply"]
                    previous = reply.get("text") or reply["generated"].get(reply["tone"], "")
                    if " ".join(raw[field].split()) == " ".join(previous.split()):
                        raise ValueError(
                            "text.unchanged_reply: provide a new formulation while preserving "
                            "language, scope position, facts and commercial terms"
                        )
                    if cosmetic_reply(previous, raw[field]):
                        raise ValueError(
                            "text.cosmetic_reply: provide a new formulation "
                            "preserving facts and terms"
                        )
                validate_text(field, raw[field], target, facts)
                if facts.get("action") == "translate":
                    reply = facts["document"]["reply"]
                    source = reply["text"] if field == reply["tone"] else reply["generated"][field]
                    preserve_translation(field, source, raw[field], reply["language"], target)
        elif stage == "change_order":
            applicable = accepted.get("hasAdditionalWork", accepted["verdict"] == "out_of_scope")
            if raw["applicable"] != (applicable and accepted["verdict"] != "in_scope"):
                raise ValueError("change_order.applicable: preserve accepted additional work")
            fields = ("description", "timelineImpact", "rationale", "note", "additionalTerms")
            group = " ".join(raw[f] for f in fields)
            for field in fields:
                if (
                    facts.get("action") != "translate"
                    and field in ("description", "timelineImpact", "note")
                    and not raw[field].strip()
                ):
                    raise ValueError(f"{field}.required: must be non-empty")
                if raw[field]:
                    validate_text(field, raw[field], target, facts, group=group)
                source = (facts.get("document", {}).get("changeOrder") or {}).get(field, "")
                if facts.get("action") == "translate":
                    preserve_translation(
                        field, source, raw[field], facts["document"]["reply"]["language"], target
                    )
            label_group = " ".join(raw["labels"].values())
            for field, label in raw["labels"].items():
                if not label.strip():
                    raise ValueError(f"labels.{field}.required: must be non-empty")
                validate_text(
                    "labels." + field,
                    label,
                    target,
                    facts,
                    check_position=False,
                    label_group=label_group
                    if field not in ("introduction", "outsideScopeFree")
                    else None,
                    reviewed_labels=reviewed_labels,
                )
        elif stage == "estimate":
            if raw["currency"] != facts["project"]["currency"]:
                raise ValueError("estimate.currency: preserve frozen currency")
            if facts["project"].get("pricingModel") == "hourly":
                price = Decimal(str(raw["estimatedHours"])) * Decimal(
                    facts["project"]["hourlyRate"]
                )
                if Decimal(raw["additionalCost"]) != price.quantize(Decimal(".01")):
                    raise ValueError("estimate.additionalCost: hours times frozen hourly rate")
            validate_text(
                "rationale",
                raw["rationale"],
                target,
                {**facts, "analysis": {**accepted, "changeOrder": raw}},
            )
    return raw


def prompt(stage, facts):
    return stage_prompt(stage, facts)


class StructuredStageRunner:
    def __init__(self, gateway, store):
        self.gateway, self.store = gateway, store
        self.reviewer = SemanticReviewer(gateway, store)

    async def run(self, binding, stage, facts, record):
        schema = TYPES[stage]
        labels = (
            reviewed_stage_labels(facts["selection"]["selectedLanguage"])
            if stage == "change_order"
            else None
        )
        if labels:
            schema = ChangeOrderProseStage

        def compose(data):
            raw = data.model_dump()
            return {**raw, "labels": dict(labels)} if labels else raw

        if record.get("candidate"):
            try:
                value = schema.model_validate_json(record["candidate"])
                raw = validate_stage(stage, compose(value), facts, reviewed_labels=labels is None)
                await self.reviewer.review(binding, stage, facts, raw, record["semantic_attempt"])
                return raw
            except (ValueError, TypeError) as error:
                message = (
                    "output.structure: "
                    + "; ".join(
                        ".".join(map(str, e["loc"])) + ": " + e["type"]
                        for e in error.errors(include_input=False)
                    )
                    if isinstance(error, ValidationError)
                    else str(error)[:500]
                )
                record = {**record, "feedback": {"rule": message}}
                await self.store.feedback(binding, record["feedback"])
        remaining = 3 - binding.semantic_start
        if remaining <= 0:
            raise GatewayFailure("semanticAttemptsExhausted")
        instructions, user = prompt(stage, facts)
        if record.get("feedback"):
            user += "\nValidation feedback: " + json.dumps(record["feedback"])
        model = GatewayResponsesModel(self.gateway, binding, record.get("prepared_request"))
        agent = Agent(
            model=model,
            output_type=NativeOutput(schema, name=stage + "_v1", strict=True),
            instructions=instructions,
            retries={"output": remaining - 1},
        )

        @agent.output_validator
        async def validator(data):
            try:
                raw = validate_stage(stage, compose(data), facts, reviewed_labels=labels is None)
                await self.reviewer.review(binding, stage, facts, raw, model.semantic)
            except ValueError as error:
                message = str(error)
                await self.store.feedback(binding, {"rule": message})
                raise ModelRetry(message) from error
            return data

        try:
            result = await agent.run(user)
        except UnexpectedModelBehavior:
            raise GatewayFailure("semanticAttemptsExhausted") from None
        return compose(result.output)
