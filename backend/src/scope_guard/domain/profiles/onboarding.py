"""Monotonic first-use transitions. Terminal decisions always win stale delivery."""

from scope_guard.domain.drafts.workflow import WorkflowError

EVENTS = {"form_opened": 0, "project_saved": 1, "check_submitted": 2, "result_viewed": 3}


def transition(status: str, step: int, event: str) -> tuple[str, int]:
    if event not in {*EVENTS, "skip"}:
        raise WorkflowError("profileInvalid")
    if status in {"completed", "skipped"}:
        return status, step
    if event == "skip":
        return "skipped", step
    if EVENTS[event] != step:
        return status, step
    return ("completed", 4) if step == 3 else ("in_progress", step + 1)
