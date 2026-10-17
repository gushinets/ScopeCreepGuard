"""UTC calendar metrics calculated from committed observations, never counter deltas."""

from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import Any


class QualityNote(StrEnum):
    LEGACY_HISTORY = "legacy_history_without_verified_completion"
    UNKNOWN_START = "operation_start_unknown"
    AI_USAGE = "ai_input_output_usage_incomplete"
    AI_OPTIONAL_USAGE = "ai_cached_or_reasoning_usage_incomplete"
    AI_COST = "ai_estimated_cost_incomplete"
    CURRENT_DAY = "report_day_incomplete"


@dataclass(frozen=True)
class Snapshot:
    cutoff: datetime
    profiles: list[dict[str, Any]] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)
    orders: list[dict[str, Any]] = field(default_factory=list)
    operations: list[dict[str, Any]] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)
    legacy_history: bool = False


def instant(value: datetime | str) -> datetime:
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if parsed.tzinfo is None:
        raise ValueError("metrics_requires_timezone")
    return parsed.astimezone(UTC)


def percent(numerator: int, denominator: int) -> Decimal | None:
    return Decimal(numerator) * 100 / denominator if denominator else None


def percentile(values: list[Decimal], fraction: str) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    position = Decimal(len(ordered) - 1) * Decimal(fraction)
    index = int(position)
    return ordered[index] + (ordered[min(index + 1, len(ordered) - 1)] - ordered[index]) * (
        position - index
    )


def calculate(snapshot: Snapshot, report_date: date) -> dict[str, Any]:
    """One row; population cutoff is min(day end, committed-source cutoff).

    Source projection deduplicates explicit saved checks by run and current feedback.
    Unknown optional tokens do not make input/output usage unknown; each token total
    independently remains NULL if any physical call lacks that observation.
    """
    start = datetime.combine(report_date, time.min, UTC)
    day_end = start + timedelta(days=1)
    cutoff = min(day_end, instant(snapshot.cutoff))
    window = start - timedelta(days=29)
    profiles = {
        p["id"]: instant(p["registered_at"])
        for p in snapshot.profiles
        if not p.get("analytics_excluded", False) and instant(p["registered_at"]) < cutoff
    }
    checks = [
        c
        for c in snapshot.checks
        if c["profile_id"] in profiles and instant(c["completed_at"]) < cutoff
    ]
    orders = [
        o
        for o in snapshot.orders
        if o["profile_id"] in profiles and instant(o["finalized_at"]) < cutoff
    ]
    operations = [o for o in snapshot.operations if o["profile_id"] in profiles]
    activity = [(c["profile_id"], instant(c["completed_at"])) for c in checks] + [
        (o["profile_id"], instant(o["finalized_at"])) for o in orders
    ]
    dau = {p for p, stamp in activity if start <= stamp < cutoff}
    mau = {p for p, stamp in activity if window <= stamp < cutoff}
    first: dict[str, datetime] = {}
    for check in checks:
        owner, stamp = check["profile_id"], instant(check["completed_at"])
        if stamp >= profiles[owner]:
            first[owner] = min(first.get(owner, stamp), stamp)
    timely = {p: stamp for p, stamp in first.items() if stamp < profiles[p] + timedelta(days=7)}
    eligible = {p for p, stamp in profiles.items() if stamp + timedelta(days=7) <= cutoff}
    ttv = [Decimal(str((stamp - profiles[p]).total_seconds())) for p, stamp in first.items()]
    check_counts = Counter(
        c["profile_id"] for c in checks if window <= instant(c["completed_at"]) < cutoff
    )
    order_owners = {
        o["profile_id"] for o in orders if window <= instant(o["finalized_at"]) < cutoff
    }
    today_checks = [c for c in checks if start <= instant(c["completed_at"]) < cutoff]
    today_orders = [o for o in orders if start <= instant(o["finalized_at"]) < cutoff]
    notes: set[QualityNote] = set()
    if snapshot.legacy_history:
        notes.add(QualityNote.LEGACY_HISTORY)
    if day_end > instant(snapshot.cutoff):
        notes.add(QualityNote.CURRENT_DAY)
    row: dict[str, Any] = {
        "report_date": report_date,
        "data_through": snapshot.cutoff,
        "definition_version": 1,
        "registered_profiles": len(profiles),
        "new_profiles": sum(start <= stamp < cutoff for stamp in profiles.values()),
        "dau": len(dau),
        "mau": len(mau),
        "stickiness_percent": percent(len(dau), len(mau)),
        "activation_eligible_profiles": len(eligible),
        "activated_profiles": len(eligible & timely.keys()),
        "activation_rate_percent": percent(len(eligible & timely.keys()), len(eligible)),
        "ttv_sample_size": len(ttv),
        "time_to_value_median_seconds": percentile(ttv, "0.5"),
        "pql_profiles": sum(check_counts[p] >= 3 for p in order_owners),
        "change_orders_created": len(today_orders),
        "change_orders_voided": sum(
            bool(o.get("voided_at")) and start <= instant(o["voided_at"]) < cutoff for o in orders
        ),
    }
    for days in (7, 30):
        cohort = {
            p for p, stamp in timely.items() if stamp.date() == report_date - timedelta(days=days)
        }
        row[f"retention_d{days}_base"] = len(cohort)
        row[f"retention_d{days}_returned"] = len(cohort & dau)
        row[f"retention_d{days}_percent"] = (
            percent(len(cohort & dau), len(cohort)) if day_end <= snapshot.cutoff else None
        )
    terminal = [
        o
        for o in operations
        if o.get("finished_at")
        and start <= instant(o["finished_at"]) < cutoff
        and o["status"] in ("succeeded", "failed", "cancelled")
    ]
    kinds = ("check", "regeneration", "translation", "estimate")
    terminal = [o for o in terminal if o["kind"] in kinds]
    for kind in (*kinds, "operation"):
        observed = terminal if kind == "operation" else [o for o in terminal if o["kind"] == kind]
        counts = Counter(o["status"] for o in observed)
        if kind != "operation":
            row[f"{kind}_started"] = sum(
                o["kind"] == kind
                and bool(o.get("created_at"))
                and start <= instant(o["created_at"]) < cutoff
                for o in operations
            )
        for status in ("succeeded", "failed", "cancelled"):
            row[f"{'operations' if kind == 'operation' else kind}_{status}"] = counts[status]
        row[f"{kind}_success_percent"] = percent(counts["succeeded"], len(observed))
        durations = [
            Decimal(str((instant(o["finished_at"]) - instant(o["created_at"])).total_seconds()))
            * 1000
            for o in observed
            if o.get("created_at") and instant(o["finished_at"]) >= instant(o["created_at"])
        ]
        row[f"{kind}_duration_sample_size"] = len(durations)
        row[f"{kind}_duration_median_ms"] = percentile(durations, "0.5")
        row[f"{kind}_duration_p95_ms"] = percentile(durations, "0.95")
        if len(durations) < len(observed):
            notes.add(QualityNote.UNKNOWN_START)
    for feature, owners in {
        "analysis": {c["profile_id"] for c in today_checks},
        "change_order": {o["profile_id"] for o in today_orders},
        **{
            kind: {
                o["profile_id"]
                for o in terminal
                if o["kind"] == kind and o["status"] == "succeeded"
            }
            for kind in ("regeneration", "translation")
        },
    }.items():
        row[f"{feature}_users"] = len(owners & dau)
        row[f"{feature}_adoption_percent"] = percent(len(owners & dau), len(dau))
    feedback = Counter(c.get("accuracy") for c in today_checks)
    for label in ("correct", "wrong", "debatable"):
        row[f"verdict_{label}"] = feedback[label]
    evaluated = sum(feedback[label] for label in ("correct", "wrong", "debatable"))
    row["verdict_evaluated_checks"] = evaluated
    row["verdict_feedback_percent"] = percent(evaluated, len(today_checks))
    calls = [
        c
        for c in snapshot.calls
        if c["profile_id"] in profiles and start <= instant(c["started_at"]) < cutoff
    ]
    row["ai_calls"] = len(calls)
    row["ai_retries"] = sum(c["semantic_attempt"] > 1 or c["transport_attempt"] > 1 for c in calls)
    for token in ("input_tokens", "output_tokens", "cached_tokens", "reasoning_tokens"):
        row[token] = (
            None if any(c.get(token) is None for c in calls) else sum(c[token] for c in calls)
        )
    row["ai_usage_unknown_calls"] = sum(
        c.get("input_tokens") is None or c.get("output_tokens") is None for c in calls
    )
    row["ai_cost_unknown_calls"] = sum(c.get("estimated_cost") is None for c in calls)
    row["ai_estimated_cost_usd"] = (
        None
        if row["ai_cost_unknown_calls"]
        else sum((Decimal(str(c["estimated_cost"])) for c in calls), Decimal(0))
    )
    if row["ai_usage_unknown_calls"]:
        notes.add(QualityNote.AI_USAGE)
    if any(c.get("cached_tokens") is None or c.get("reasoning_tokens") is None for c in calls):
        notes.add(QualityNote.AI_OPTIONAL_USAGE)
    if row["ai_cost_unknown_calls"]:
        notes.add(QualityNote.AI_COST)
    for status in ("accepted", "rejected"):
        row[f"validation_{status}"] = sum(c.get("validation_status") == status for c in calls)
    row["validation_rejection_percent"] = percent(
        row["validation_rejected"], row["validation_accepted"] + row["validation_rejected"]
    )
    row["is_partial"] = bool(notes)
    row["quality_notes"] = sorted(notes)
    return row
