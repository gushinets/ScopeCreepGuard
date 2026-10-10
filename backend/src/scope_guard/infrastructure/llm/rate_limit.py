"""Single-process rolling limiter. Admission contains no suspension points."""

from threading import Lock


class GenerationLimiter:
    def __init__(self):
        self._timestamps: dict[str, list[int]] = {}
        self._lock = Lock()

    def allow(self, user_id: str, now_ms: int) -> bool:
        with self._lock:
            recent = [t for t in self._timestamps.get(user_id, ()) if t > now_ms - 60_000]
            self._timestamps[user_id] = recent
            if len(recent) >= 10:
                return False
            recent.append(now_ms)
            return True
