"""Durable, read-only content observations, executed after user publication."""

import asyncio
import re
from copy import deepcopy
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from scope_guard.domain.llm.reply_similarity import (
    MAX_REPLY_COMPARISON_LENGTH,
    REPLY_SIMILARITY_THRESHOLD,
    compare_replies,
    previous_reply,
)
from scope_guard.domain.llm.runtime import PROMPT_VERSION, Binding, GatewayFailure, digest
from scope_guard.integrations.llm.semantic_review import SemanticReviewer


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: UUID
    stage_id: UUID
    stage: str
    rule: str
    version: str = "content-diagnostics-v1"
    field: str
    outcome: Literal["pass", "finding", "uncertain", "diagnostic_error"]
    confidence: float | None = Field(default=None, ge=0, le=1)
    expected: str | None = None
    observed: str | None = None
    score: float | None = None
    threshold: float | None = None
    attempt: int | None = None
    novelty_exhausted: bool | None = None
    skipped_reason: str | None = None
    comparison_limit: int | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


def local_observation(binding, stage, check):

    base = dict(operation_id=binding.operation_id, stage_id=binding.step_id, stage=stage)
    try:
        check()
        return [Observation(**base, field="*", rule="content", outcome="pass")]
    except ValueError as error:
        # Only allow normalized rule/path identifiers and language/confidence values.
        # Never retain the exception message: it may include customer prose.
        message = str(error)
        path = message.split(":", 1)[0]
        if not re.fullmatch(r"[A-Za-z_]+(?:\.[A-Za-z_]+)*", path):
            return [Observation(**base, field="*", rule="content", outcome="diagnostic_error")]
        field, _, rule = path.rpartition(".")
        confidence = re.search(r"confidence (0(?:\.\d+)?|1(?:\.0+)?)\b", message)
        languages = re.search(
            r"expected ([a-z]{2}(?:-[A-Za-z]+)?); detected ([a-z]{2}|None)", message
        )
        return [
            Observation(
                **base,
                field=field or path,
                rule=rule or "content",
                outcome="finding",
                confidence=float(confidence[1]) if confidence else None,
                expected=languages[1] if languages else None,
                observed=languages[2] if languages else None,
            )
        ]
    except Exception:
        return [Observation(**base, field="*", rule="content", outcome="diagnostic_error")]


def local_observations(binding, stage, candidate, facts, *, novelty=None):
    from scope_guard.integrations.llm.preservation import preserve_translation
    from scope_guard.integrations.llm.stages import validate_stage, validate_text

    checks = [lambda: validate_stage(stage, candidate, facts)]
    fields = (
        ("warm", "neutral", "firm")
        if stage == "replies"
        else ("text",)
        if stage == "reply"
        else ("description", "timelineImpact", "rationale", "note", "additionalTerms")
        if stage == "change_order"
        else ("summary", "reasoning", "suggestion")
        if stage == "analysis"
        else ("rationale",)
    )
    target = facts["locale"] if stage == "analysis" else facts["selection"]["selectedLanguage"]
    for field in fields:
        if candidate.get(field):
            checks.append(
                lambda field=field: validate_text(
                    field, candidate[field], target, facts, analysis=stage == "analysis"
                )
            )
        if facts.get("action") == "translate":
            document = facts["document"]
            if stage == "replies":
                reply = document["reply"]
                original = reply["text"] if field == reply["tone"] else reply["generated"][field]
            elif stage == "change_order":
                original = document["changeOrder"].get(field, "")
            else:
                continue
            checks.append(
                lambda field=field, original=original, document=document: preserve_translation(
                    field, original, candidate[field], document["reply"]["language"], target
                )
            )
    observations = [o for check in checks for o in local_observation(binding, stage, check)]
    if stage == "reply" and facts.get("action") == "regenerate":
        try:
            comparison = compare_replies(previous_reply(facts), candidate["text"])
            score = comparison.score
            observations.append(
                Observation(
                    operation_id=binding.operation_id,
                    stage_id=binding.step_id,
                    stage=stage,
                    field="text",
                    rule="reply_similarity",
                    outcome="uncertain"
                    if score is None
                    else "finding"
                    if score >= REPLY_SIMILARITY_THRESHOLD
                    else "pass",
                    score=score,
                    threshold=REPLY_SIMILARITY_THRESHOLD,
                    attempt=(novelty or {}).get("exhaustedAttempt", (novelty or {}).get("attempt")),
                    novelty_exhausted=(novelty or {}).get("exhausted"),
                    skipped_reason=comparison.skipped_reason,
                    comparison_limit=MAX_REPLY_COMPARISON_LENGTH,
                )
            )
        except ValueError:
            observations.append(
                Observation(
                    operation_id=binding.operation_id,
                    stage_id=binding.step_id,
                    stage=stage,
                    field="text",
                    rule="reply_similarity",
                    outcome="diagnostic_error",
                )
            )
    unique = {(o.field, o.rule, o.outcome): o for o in observations}
    return list(unique.values())


async def execute_diagnostics(runner, operation):
    if operation["frozen_input"].get("contract") != "diagnostics-v1":
        raise GatewayFailure("workflowVersionUnavailable")
    store = runner.store
    parent = await store.get(operation["owner_id"], UUID(operation["frozen_input"]["parentId"]))
    facts = deepcopy(parent["frozen_input"])
    steps = await store.steps(parent["id"])
    if parent["kind"] == "check":
        facts["analysis"] = next(
            s["accepted_result"] for s in steps if s["stage_key"] == "analysis"
        )
    if parent["kind"] == "agreement" and facts.get("prepareEstimate"):
        estimate = next(s["accepted_result"] for s in steps if s["stage_key"] == "estimate")
        facts["analysis"].update(
            {k: estimate[k] for k in ("estimatedHours", "additionalCost", "currency")}
        )
    records = {s["stage_key"]: s for s in await store.steps(operation["id"])}
    for source in steps:
        stage, candidate = source["stage_key"], source["accepted_result"]
        record = records.get(stage + "_diagnostic")
        if not record or record["status"] == "accepted":
            continue
        binding = Binding(
            operation["id"],
            record["id"],
            operation["epoch"],
            operation["policy"]["model"],
            "medium",
            deadline=operation["deadline_at"],
        )
        if record["prompt_version"] != PROMPT_VERSION:
            raise GatewayFailure("workflowVersionUnavailable")
        await store.freeze_stage(binding, digest({"sourceStep": str(source["id"])}))
        observations = await asyncio.to_thread(
            local_observations,
            binding,
            stage,
            candidate,
            facts,
            novelty=(source.get("feedback") or {}).get("novelty"),
        )
        if stage != "analysis":
            try:
                decision = await SemanticReviewer(runner.gateway, store).review(
                    binding, stage, facts, candidate, 1
                )
                if decision.decision == "accept":
                    observations.append(
                        Observation(
                            operation_id=binding.operation_id,
                            stage_id=binding.step_id,
                            stage=stage,
                            field="*",
                            rule="semantic_review",
                            outcome="pass",
                        )
                    )
                else:
                    observations.extend(
                        Observation(
                            operation_id=binding.operation_id,
                            stage_id=binding.step_id,
                            stage=stage,
                            field=v.field,
                            rule=v.rule,
                            outcome="uncertain" if decision.decision == "uncertain" else "finding",
                        )
                        for v in decision.violations
                    )
            except Exception:
                observations.append(
                    Observation(
                        operation_id=binding.operation_id,
                        stage_id=binding.step_id,
                        stage=stage,
                        field="*",
                        rule="semantic_review",
                        outcome="diagnostic_error",
                    )
                )
        await store.accept(
            binding, {"observations": [o.model_dump(mode="json") for o in observations]}
        )
    await store.finish_diagnostics(operation)
