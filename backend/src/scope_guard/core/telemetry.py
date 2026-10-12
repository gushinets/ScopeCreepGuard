import json
import logging
from contextvars import ContextVar

correlation_id: ContextVar[str] = ContextVar("generation_correlation_id", default="")
logger = logging.getLogger("scope_guard.generation")


def log_event(event: str, **fields):
    # Callers supply internal operation names and numeric/bounded metadata only.
    logger.info(
        json.dumps(
            {"event": event, "correlation_id": correlation_id.get(), **fields},
            separators=(",", ":"),
        )
    )
