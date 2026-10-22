import pytest

from scope_guard.domain.profiles.onboarding import transition


def test_only_ordered_actions_advance_and_repeated_actions_are_safe():
    state = ("not_started", 0)
    assert transition(*state, "project_saved") == state
    for event in ("form_opened", "project_saved", "check_submitted", "result_viewed"):
        state = transition(*state, event)
        assert transition(*state, event) == state
    assert state == ("completed", 4)


@pytest.mark.parametrize("step", range(4))
def test_skip_is_terminal_at_every_step(step):
    status = "not_started" if step == 0 else "in_progress"
    state = transition(status, step, "skip")
    for event in ("form_opened", "project_saved", "check_submitted", "result_viewed", "skip"):
        assert transition(*state, event) == state


def test_completed_cannot_be_reactivated_or_replaced_by_skip():
    for event in ("form_opened", "project_saved", "check_submitted", "result_viewed", "skip"):
        assert transition("completed", 4, event) == ("completed", 4)
