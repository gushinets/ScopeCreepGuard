"""Text novelty through the real PydanticAI/gateway boundary, without paid calls."""

import asyncio
from copy import deepcopy

import pytest
from fixtures.llm_review import PROSE, facts
from test_llm_review_corrections import RecordingStore, run


@pytest.mark.parametrize(
    "candidate",
    [
        PROSE["en"],
        PROSE["en"].upper(),
        "  " + PROSE["en"].replace(" ", "\n  "),
        PROSE["en"] + " Thank you.",
    ],
)
def test_similar_reply_requests_another_formulation(candidate):
    source, store = facts(action="regenerate"), RecordingStore()
    different = "A separate proposal needs your sign-off before we proceed with these additions."
    result = asyncio.run(
        run(
            "reply",
            source,
            [{"scopePosition": "out_of_scope", "text": text} for text in (candidate, different)],
            store,
        )
    )
    assert result["text"] == different
    assert len(store.calls) == 2
    assert "text.reply_similarity" in store.feedbacks[0]["rule"]


def test_exhaustion_returns_latest_valid_after_malformed_attempt():
    source, store = facts(action="regenerate"), RecordingStore()
    previous = deepcopy(source)
    latest = PROSE["en"] + " Thank you."
    result = asyncio.run(
        run(
            "reply",
            source,
            [
                {"scopePosition": "out_of_scope", "text": PROSE["en"]},
                {"scopePosition": "out_of_scope", "text": latest},
                {},
            ],
            store,
        )
    )
    assert result["text"] == latest
    assert len(store.calls) == 3
    assert source == previous


@pytest.mark.parametrize(
    ("previous", "candidate", "expected"),
    [
        ("Привет, МИР!", " привет — мир ", 1.0),
        ("Ｆｕｌｌ Ｗｉｄｔｈ", "full width", 1.0),
        ("¡HOLA, SEÑOR!", "hola señor", 1.0),
        ("Straße", "STRASSE", 1.0),
        ("", "new reply", None),
        (" — ! ", "new reply", None),
        ("old", "", 0.0),
        ("abcdefghijklmnopqrxxxxxxx", "abcdefghijklmnopqryyyyyyy", 0.72),
        ("abcdefghijklmnopqxxxxxxxx", "abcdefghijklmnopqyyyyyyyy", 0.68),
    ],
)
def test_normalized_score(previous, candidate, expected):
    from scope_guard.domain.llm.reply_similarity import reply_similarity

    assert reply_similarity(previous, candidate) == expected


@pytest.mark.parametrize(
    ("candidate", "calls"), [("abcdefghijklmnopqryyyyyyy", 2), ("abcdefghijklmnopqyyyyyyyy", 1)]
)
def test_threshold_is_inclusive(candidate, calls):
    source, store = facts(action="regenerate"), RecordingStore()
    source["document"]["reply"]["text"] = "abcdefghijklmnopqrxxxxxxx"
    result = asyncio.run(
        run(
            "reply",
            source,
            [
                {"scopePosition": "out_of_scope", "text": candidate},
                {"scopePosition": "out_of_scope", "text": "completely different wording"},
            ],
            store,
        )
    )
    assert len(store.calls) == calls
    assert result["text"] == (candidate if calls == 1 else "completely different wording")


@pytest.mark.parametrize("action", ["check", "translate", "estimate", "agreement"])
def test_nonregeneration_does_not_check_novelty(action):
    source, store = facts(action=action), RecordingStore()
    candidate = {"scopePosition": "out_of_scope", "text": PROSE["en"]}
    assert asyncio.run(run("reply", source, [candidate], store)) == candidate
    assert len(store.calls) == 1


def test_shared_budget_includes_structural_errors():
    source, store = facts(action="regenerate"), RecordingStore()
    result = asyncio.run(
        run(
            "reply", source, [{}, {"scopePosition": "out_of_scope", "text": PROSE["en"]}, {}], store
        )
    )
    assert result["text"] == PROSE["en"]
    assert [c["request"].semantic_attempt for c in store.calls] == [1, 2, 3]


def test_no_valid_candidate_fails():
    from scope_guard.domain.llm.runtime import GatewayFailure

    source, store = facts(action="regenerate"), RecordingStore()
    with pytest.raises(GatewayFailure, match="semanticAttemptsExhausted"):
        asyncio.run(run("reply", source, [{}], store))
    assert len(store.calls) == 3


def test_comparison_uses_original_saved_manual_reply():
    source, store = facts(action="regenerate"), RecordingStore()
    source["document"]["reply"]["text"] = "a" * 100
    before = deepcopy(source)
    # Second candidate is close to the rejected candidate but below the threshold
    # against the frozen manual edit. Comparing with the last attempt rejects it.
    one, two = "a" * 80 + "b" * 20, "a" * 60 + "b" * 40
    result = asyncio.run(
        run(
            "reply",
            source,
            [{"scopePosition": "out_of_scope", "text": t} for t in (one, two)],
            store,
        )
    )
    assert result["text"] == two and len(store.calls) == 2
    assert source == before


def test_empty_previous_uses_generated_tone_fallback():
    source, store = facts(action="regenerate", tone="firm"), RecordingStore()
    source["document"]["reply"]["text"] = ""
    asyncio.run(
        run("reply", source, [{"scopePosition": "out_of_scope", "text": PROSE["en"]}], store)
    )
    assert len(store.calls) == 3


def test_empty_normalized_previous_skips_check_but_empty_candidate_is_invalid():
    from scope_guard.domain.llm.runtime import GatewayFailure

    source, store = facts(action="regenerate"), RecordingStore()
    source["document"]["reply"]["text"] = "!!!"
    result = asyncio.run(
        run("reply", source, [{"scopePosition": "out_of_scope", "text": "New reply"}], store)
    )
    assert result["text"] == "New reply" and len(store.calls) == 1
    with pytest.raises(GatewayFailure, match="semanticAttemptsExhausted"):
        asyncio.run(
            run("reply", source, [{"scopePosition": "out_of_scope", "text": ""}], RecordingStore())
        )


def test_comparison_limit_never_truncates():
    from scope_guard.domain.llm.reply_similarity import reply_similarity

    with pytest.raises(ValueError, match="text.length"):
        reply_similarity("a" * 32769, "a")


def test_comparison_keeps_worker_heartbeat_responsive(monkeypatch):
    import threading

    from scope_guard.domain.llm.reply_similarity import reply_similarity
    from scope_guard.integrations.llm import stages

    renewed = threading.Event()

    def slow_comparison(previous, candidate):
        assert renewed.wait(2), "comparison blocked the lease heartbeat"
        return reply_similarity(previous, candidate)

    monkeypatch.setattr(stages, "reply_similarity", slow_comparison)

    async def exercise():
        async def heartbeat():
            await asyncio.sleep(0.01)
            renewed.set()

        result, _ = await asyncio.gather(
            run(
                "reply",
                facts(action="regenerate"),
                [
                    {
                        "scopePosition": "out_of_scope",
                        "text": "Please authorize a proposal for Arrow integration.",
                    }
                ],
                RecordingStore(),
            ),
            heartbeat(),
        )
        assert result["text"] == "Please authorize a proposal for Arrow integration."

    asyncio.run(exercise())


def test_similarity_diagnostics_and_logs_contain_numeric_metadata_without_reply(caplog):
    import logging
    from uuid import uuid4

    from scope_guard.domain.llm.runtime import Binding
    from scope_guard.integrations.llm.diagnostics import local_observations

    source, store = facts(action="regenerate"), RecordingStore()
    with caplog.at_level(logging.INFO, logger="scope_guard"):
        result = asyncio.run(
            run("reply", source, [{"scopePosition": "out_of_scope", "text": PROSE["en"]}], store)
        )
    records = [r for r in caplog.records if r.msg == "reply_similarity"]
    assert records[-1].score == 1.0 and records[-1].threshold == 0.72
    assert records[-1].attempt == 3 and records[-1].novelty_exhausted is True
    assert all(PROSE["en"] not in r.getMessage() for r in records)
    observations = local_observations(
        Binding(uuid4(), uuid4(), 1, "model", "high"),
        "reply",
        result,
        source,
        novelty={"attempt": 2, "exhaustedAttempt": 3, "exhausted": True},
    )
    finding = next(o for o in observations if o.rule == "reply_similarity")
    assert finding.score == 1.0 and finding.threshold == 0.72
    assert finding.attempt == 3 and finding.novelty_exhausted is True
