from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from scope_guard.domain.marketing import Snapshot, calculate


def at(day, hour=0):
    return datetime(2026, 1, day, hour, tzinfo=UTC)


def test_mature_activation_half_open_ttv_and_distinct_adoption():
    snapshot = Snapshot(
        at(20),
        profiles=[
            {"id": "a", "registered_at": at(1)},
            {"id": "b", "registered_at": at(1)},
            {"id": "c", "registered_at": at(15)},
        ],
        checks=[
            {"id": "1", "profile_id": "a", "completed_at": at(7)},
            {"id": "2", "profile_id": "b", "completed_at": at(8)},
            {"id": "3", "profile_id": "c", "completed_at": at(19)},
        ],
        operations=[
            {
                "id": "r",
                "profile_id": "b",
                "kind": "regeneration",
                "created_at": at(19),
                "finished_at": at(19),
                "status": "succeeded",
            }
        ],
    )
    row = calculate(snapshot, date(2026, 1, 19))
    assert row["activation_eligible_profiles"] == 2
    assert row["activated_profiles"] == 1
    assert row["activation_rate_percent"] == 50
    assert row["ttv_sample_size"] == 3
    assert row["dau"] == 1 and row["mau"] == 3
    assert row["regeneration_users"] == 0
    assert row["analysis_adoption_percent"] == 100


def test_pql_feedback_void_and_calendar_windows():
    snapshot = Snapshot(
        at(31),
        profiles=[{"id": "a", "registered_at": at(1)}],
        checks=[
            {
                "id": str(i),
                "profile_id": "a",
                "completed_at": at(i),
                "accuracy": "wrong" if i == 3 else None,
            }
            for i in (1, 2, 3)
        ],
        orders=[{"id": "co", "profile_id": "a", "finalized_at": at(3), "voided_at": at(4)}],
    )
    assert calculate(snapshot, date(2026, 1, 3))["pql_profiles"] == 1
    row = calculate(snapshot, date(2026, 1, 3))
    assert row["change_orders_created"] == 1 and row["verdict_wrong"] == 1
    assert calculate(snapshot, date(2026, 1, 4))["change_orders_voided"] == 1
    assert calculate(snapshot, date(2026, 1, 31))["pql_profiles"] == 0
    assert calculate(snapshot, date(2026, 1, 8))["retention_d7_base"] == 1
    assert calculate(snapshot, date(2026, 1, 8))["retention_d7_returned"] == 0
    assert calculate(snapshot, date(2026, 1, 31))["retention_d30_percent"] is None


def test_ai_completeness_retry_or_and_observation_percentile():
    calls = [
        {
            "profile_id": "a",
            "started_at": at(2),
            "semantic_attempt": s,
            "transport_attempt": t,
            "input_tokens": 10,
            "output_tokens": 20,
            "cached_tokens": None,
            "reasoning_tokens": None,
            "estimated_cost": "0.01",
            "validation_status": "accepted",
        }
        for s, t in ((1, 1), (1, 1), (1, 2), (2, 2))
    ]
    calls[-1]["input_tokens"] = None
    calls[-1]["estimated_cost"] = None
    snapshot = Snapshot(
        at(3),
        profiles=[{"id": "a", "registered_at": at(1)}],
        calls=calls,
        operations=[
            {
                "id": str(i),
                "profile_id": "a",
                "kind": "check",
                "created_at": at(1),
                "finished_at": at(2) + timedelta(seconds=i),
                "status": "succeeded",
            }
            for i in (0, 10, 100)
        ],
    )
    row = calculate(snapshot, date(2026, 1, 2))
    assert row["ai_calls"] == 4 and row["ai_retries"] == 2
    assert row["input_tokens"] is None and row["output_tokens"] == 80
    assert row["ai_usage_unknown_calls"] == 1 and row["ai_cost_unknown_calls"] == 1
    assert row["ai_estimated_cost_usd"] is None
    assert row["check_duration_median_ms"] == Decimal(86410000)
    assert row["check_duration_p95_ms"] == Decimal(86491000)


def test_empty_denominators():
    row = calculate(Snapshot(at(3)), date(2026, 1, 2))
    assert row["dau"] == 0 and row["stickiness_percent"] is None
    assert row["operation_success_percent"] is None
    assert row["time_to_value_median_seconds"] is None


@pytest.mark.parametrize("preparation_status", ["succeeded", "failed", "cancelled"])
def test_agreement_preparation_is_not_an_agreed_product_operation(preparation_status):
    snapshot = Snapshot(
        at(3),
        profiles=[{"id": "a", "registered_at": at(1)}],
        operations=[
            {
                "id": kind,
                "profile_id": "a",
                "kind": kind,
                "created_at": at(2),
                "finished_at": at(2) + timedelta(seconds=1),
                "status": status,
            }
            for kind, status in (("check", "succeeded"), ("agreement", preparation_status))
        ],
    )
    row = calculate(snapshot, date(2026, 1, 2))
    assert row["operations_succeeded"] == row["check_succeeded"] == 1
    assert row["operations_failed"] == 0
    assert row["operations_cancelled"] == 0
    assert row["operation_success_percent"] == 100
    assert row["operation_duration_sample_size"] == 1
    assert row["dau"] == 0  # neither preparation nor an unsaved check is activity


def test_midnight_rolling_window_and_exact_retention_days():
    day = datetime(2026, 2, 1, tzinfo=UTC)
    snapshot = Snapshot(
        day + timedelta(days=1),
        profiles=[
            {"id": "a", "registered_at": day - timedelta(days=31)},
            {"id": "b", "registered_at": day - timedelta(days=30)},
        ],
        checks=[
            {"id": "old", "profile_id": "a", "completed_at": day - timedelta(days=30)},
            {"id": "edge", "profile_id": "b", "completed_at": day - timedelta(days=29)},
            {"id": "yesterday", "profile_id": "a", "completed_at": day - timedelta(microseconds=1)},
            {"id": "today", "profile_id": "a", "completed_at": day},
            {"id": "tomorrow", "profile_id": "b", "completed_at": day + timedelta(days=1)},
        ],
    )
    row = calculate(snapshot, day.date())
    assert row["dau"] == 1 and row["mau"] == 2
    assert row["retention_d30_base"] == row["retention_d30_returned"] == 1
    assert row["retention_d30_percent"] == 100
    # No return on D7, even though activity exists later in the month.
    assert calculate(snapshot, date(2026, 1, 9))["retention_d7_percent"] == 0
    expiry = Snapshot(day + timedelta(days=32), profiles=snapshot.profiles, checks=snapshot.checks)
    assert calculate(expiry, (day + timedelta(days=31)).date())["mau"] == 0


def test_exclusions_apply_to_all_populations_and_inactive_is_not_excluded():
    profile = {"id": "a", "registered_at": at(1), "status": "inactive"}
    sources = dict(
        profiles=[profile],
        checks=[
            {"id": str(i), "profile_id": "a", "completed_at": at(2), "accuracy": "correct"}
            for i in range(3)
        ],
        orders=[{"id": "c", "profile_id": "a", "finalized_at": at(2), "voided_at": at(2)}],
        operations=[
            {
                "id": "o",
                "profile_id": "a",
                "kind": "translation",
                "created_at": at(2),
                "finished_at": at(2),
                "status": "succeeded",
            }
        ],
        calls=[
            {
                "profile_id": "a",
                "started_at": at(2),
                "semantic_attempt": 2,
                "transport_attempt": 2,
                "input_tokens": 1,
                "output_tokens": 1,
                "cached_tokens": 0,
                "reasoning_tokens": 0,
                "estimated_cost": "0.1",
                "validation_status": "rejected",
            }
        ],
    )
    visible = calculate(Snapshot(at(3), **sources), date(2026, 1, 2))
    assert visible["dau"] == visible["pql_profiles"] == visible["translation_users"] == 1
    sources["profiles"] = [{**profile, "analytics_excluded": True}]
    excluded = calculate(Snapshot(at(3), **sources), date(2026, 1, 2))
    for name in (
        "registered_profiles",
        "new_profiles",
        "dau",
        "mau",
        "ttv_sample_size",
        "pql_profiles",
        "change_orders_created",
        "change_orders_voided",
        "verdict_correct",
        "translation_succeeded",
        "translation_users",
        "ai_calls",
        "ai_retries",
        "input_tokens",
        "validation_rejected",
    ):
        assert excluded[name] == 0, name


def test_mature_denominator_terminal_rates_and_unknown_legacy_duration():
    snapshot = Snapshot(
        at(8),
        profiles=[{"id": "a", "registered_at": at(1)}, {"id": "b", "registered_at": at(1, 1)}],
        checks=[{"id": "a", "profile_id": "a", "completed_at": at(2)}],
        operations=[
            {
                "id": str(i),
                "profile_id": "a",
                "kind": "regeneration",
                "created_at": None,
                "finished_at": at(7),
                "status": status,
            }
            for i, status in enumerate(("succeeded", "failed", "cancelled", "pending"))
        ],
    )
    row = calculate(snapshot, date(2026, 1, 7))
    assert row["activation_eligible_profiles"] == row["activated_profiles"] == 1
    assert row["operation_success_percent"] == Decimal(100) / 3
    assert row["operation_duration_sample_size"] == 0
    assert row["operation_duration_median_ms"] is None
    assert "operation_start_unknown" in row["quality_notes"]


def test_all_wide_columns_are_populated_and_notes_are_typed():
    from scope_guard.database.models.marketing import marketing_metrics
    from scope_guard.domain.marketing import QualityNote

    row = calculate(Snapshot(at(3)), date(2026, 1, 2))
    assert set(row) == set(marketing_metrics.c.keys()) - {"calculated_at"}
    assert all(QualityNote(note) for note in row["quality_notes"])


@pytest.mark.parametrize("checks,orders,expected", [(0, 1, 0), (2, 1, 0), (3, 0, 0), (3, 1, 1)])
def test_pql_requires_both_complete_conditions(checks, orders, expected):
    snapshot = Snapshot(
        at(3),
        profiles=[{"id": "a", "registered_at": at(1)}],
        checks=[{"id": str(i), "profile_id": "a", "completed_at": at(2)} for i in range(checks)],
        orders=[{"id": str(i), "profile_id": "a", "finalized_at": at(2)} for i in range(orders)],
    )
    assert calculate(snapshot, date(2026, 1, 2))["pql_profiles"] == expected
